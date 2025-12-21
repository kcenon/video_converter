"""Unit tests for metadata processor module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.processors.metadata import (
    GPSCoordinates,
    MetadataApplicationError,
    MetadataExtractionError,
    MetadataProcessor,
    MetadataVerificationResult,
)
from video_converter.utils.command_runner import (
    CommandNotFoundError,
    CommandResult,
    CommandRunner,
)


class TestGPSCoordinates:
    """Tests for GPSCoordinates dataclass."""

    def test_str_north_east(self) -> None:
        """Test string representation for north-east coordinates."""
        gps = GPSCoordinates(latitude=37.7749, longitude=122.4194)
        result = str(gps)
        assert "37.774900°N" in result
        assert "122.419400°E" in result

    def test_str_south_west(self) -> None:
        """Test string representation for south-west coordinates."""
        gps = GPSCoordinates(latitude=-33.8688, longitude=-151.2093)
        result = str(gps)
        assert "33.868800°S" in result
        assert "151.209300°W" in result

    def test_str_with_altitude(self) -> None:
        """Test string includes altitude when present."""
        gps = GPSCoordinates(latitude=37.0, longitude=122.0, altitude=100.5)
        result = str(gps)
        assert "100.5m" in result

    def test_str_without_altitude(self) -> None:
        """Test string excludes altitude when None."""
        gps = GPSCoordinates(latitude=37.0, longitude=122.0)
        result = str(gps)
        assert "m" not in result


class TestMetadataVerificationResult:
    """Tests for MetadataVerificationResult dataclass."""

    def test_all_matched_true(self) -> None:
        """Test all_matched is True when all tags match."""
        result = MetadataVerificationResult(
            all_matched=True,
            tag_results={"CreateDate": True, "GPSLatitude": True},
        )
        assert result.all_matched is True

    def test_all_matched_false(self) -> None:
        """Test all_matched is False when any tag doesn't match."""
        result = MetadataVerificationResult(
            all_matched=False,
            tag_results={"CreateDate": True, "GPSLatitude": False},
        )
        assert result.all_matched is False

    def test_default_empty_lists(self) -> None:
        """Test default values for lists."""
        result = MetadataVerificationResult(all_matched=True)
        assert result.tag_results == {}
        assert result.missing_in_source == []
        assert result.missing_in_dest == []


class TestMetadataProcessor:
    """Tests for MetadataProcessor class."""

    @pytest.fixture
    def mock_runner(self) -> MagicMock:
        """Create a mock CommandRunner."""
        runner = MagicMock(spec=CommandRunner)
        runner.check_command_exists.return_value = True
        runner.ensure_command_exists.return_value = None
        return runner

    @pytest.fixture
    def processor(self, mock_runner: MagicMock) -> MetadataProcessor:
        """Create a MetadataProcessor with mock runner."""
        return MetadataProcessor(mock_runner)

    @pytest.fixture
    def sample_metadata(self) -> dict:
        """Sample metadata response from exiftool."""
        return {
            "SourceFile": "/path/to/video.mp4",
            "QuickTime:CreateDate": "2024:01:15 10:30:00",
            "QuickTime:ModifyDate": "2024:01:15 10:30:00",
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
            "Composite:GPSAltitude": 10.5,
            "QuickTime:Make": "Apple",
            "QuickTime:Model": "iPhone 14 Pro",
            "QuickTime:Duration": "00:01:30",
            "Composite:Rotation": 0,
        }

    def test_init_with_runner(self, mock_runner: MagicMock) -> None:
        """Test initialization with provided runner."""
        processor = MetadataProcessor(mock_runner)
        assert processor._runner is mock_runner

    def test_init_without_runner(self) -> None:
        """Test initialization creates default runner."""
        processor = MetadataProcessor()
        assert processor._runner is not None
        assert isinstance(processor._runner, CommandRunner)

    def test_is_available_true(self, mock_runner: MagicMock) -> None:
        """Test is_available returns True when exiftool exists."""
        mock_runner.check_command_exists.return_value = True
        processor = MetadataProcessor(mock_runner)
        assert processor.is_available() is True
        mock_runner.check_command_exists.assert_called_with("exiftool")

    def test_is_available_false(self, mock_runner: MagicMock) -> None:
        """Test is_available returns False when exiftool doesn't exist."""
        mock_runner.check_command_exists.return_value = False
        processor = MetadataProcessor(mock_runner)
        assert processor.is_available() is False

    def test_ensure_available_success(self, processor: MetadataProcessor) -> None:
        """Test ensure_available doesn't raise when exiftool exists."""
        processor.ensure_available()  # Should not raise

    def test_ensure_available_raises(self, mock_runner: MagicMock) -> None:
        """Test ensure_available raises when exiftool doesn't exist."""
        mock_runner.ensure_command_exists.side_effect = CommandNotFoundError("exiftool")
        processor = MetadataProcessor(mock_runner)
        with pytest.raises(CommandNotFoundError):
            processor.ensure_available()

    def test_extract_success(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        sample_metadata: dict,
        tmp_path: Path,
    ) -> None:
        """Test successful metadata extraction."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([sample_metadata]),
            stderr="",
        )

        result = processor.extract(video_file)

        assert result["QuickTime:CreateDate"] == "2024:01:15 10:30:00"
        assert result["Composite:GPSLatitude"] == 37.7749

    def test_extract_file_not_found(self, processor: MetadataProcessor) -> None:
        """Test extract raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            processor.extract(Path("/nonexistent/video.mp4"))

    def test_extract_empty_result(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test extract returns empty dict for empty response."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout="[]",
            stderr="",
        )

        result = processor.extract(video_file)
        assert result == {}

    def test_extract_command_fails(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test extract raises MetadataExtractionError on failure."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=1,
            stdout="",
            stderr="Error reading file",
        )

        with pytest.raises(MetadataExtractionError) as exc_info:
            processor.extract(video_file)

        assert "Error reading file" in str(exc_info.value)

    def test_extract_invalid_json(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test extract raises MetadataExtractionError on invalid JSON."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout="not valid json",
            stderr="",
        )

        with pytest.raises(MetadataExtractionError) as exc_info:
            processor.extract(video_file)

        assert "Invalid JSON" in str(exc_info.value)

    def test_extract_gps_success(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        sample_metadata: dict,
        tmp_path: Path,
    ) -> None:
        """Test successful GPS extraction."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([sample_metadata]),
            stderr="",
        )

        gps = processor.extract_gps(video_file)

        assert gps is not None
        assert gps.latitude == pytest.approx(37.7749)
        assert gps.longitude == pytest.approx(-122.4194)
        assert gps.altitude == pytest.approx(10.5)

    def test_extract_gps_no_gps_data(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test extract_gps returns None when no GPS data."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([{"SourceFile": "/video.mp4"}]),
            stderr="",
        )

        gps = processor.extract_gps(video_file)
        assert gps is None

    def test_copy_all_success(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful copy_all operation."""
        source = tmp_path / "source.mp4"
        dest = tmp_path / "dest.mp4"
        source.touch()
        dest.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout="1 image files updated",
            stderr="",
        )

        result = processor.copy_all(source, dest)

        assert result is True
        # Verify command structure
        call_args = mock_runner.run.call_args[0][0]
        assert "exiftool" in call_args
        assert "-overwrite_original" in call_args
        assert "-tagsFromFile" in call_args
        assert "-all:all" in call_args

    def test_copy_all_source_not_found(
        self,
        processor: MetadataProcessor,
        tmp_path: Path,
    ) -> None:
        """Test copy_all raises FileNotFoundError for missing source."""
        dest = tmp_path / "dest.mp4"
        dest.touch()

        with pytest.raises(FileNotFoundError) as exc_info:
            processor.copy_all(Path("/nonexistent.mp4"), dest)

        assert "Source file" in str(exc_info.value)

    def test_copy_all_dest_not_found(
        self,
        processor: MetadataProcessor,
        tmp_path: Path,
    ) -> None:
        """Test copy_all raises FileNotFoundError for missing dest."""
        source = tmp_path / "source.mp4"
        source.touch()

        with pytest.raises(FileNotFoundError) as exc_info:
            processor.copy_all(source, Path("/nonexistent.mp4"))

        assert "Destination file" in str(exc_info.value)

    def test_copy_tags_success(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful copy_tags operation."""
        source = tmp_path / "source.mp4"
        dest = tmp_path / "dest.mp4"
        source.touch()
        dest.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout="1 image files updated",
            stderr="",
        )

        result = processor.copy_tags(source, dest, ["GPS*", "CreateDate"])

        assert result is True
        call_args = mock_runner.run.call_args[0][0]
        assert "-GPS*" in call_args
        assert "-CreateDate" in call_args

    def test_copy_tags_empty_list(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test copy_tags returns True for empty tag list."""
        source = tmp_path / "source.mp4"
        dest = tmp_path / "dest.mp4"
        source.touch()
        dest.touch()

        result = processor.copy_tags(source, dest, [])

        assert result is True
        mock_runner.run.assert_not_called()

    def test_copy_gps(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test copy_gps copies GPS-related tags."""
        source = tmp_path / "source.mp4"
        dest = tmp_path / "dest.mp4"
        source.touch()
        dest.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout="1 image files updated",
            stderr="",
        )

        result = processor.copy_gps(source, dest)

        assert result is True
        call_args = mock_runner.run.call_args[0][0]
        assert "-GPS*" in call_args

    def test_copy_dates(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test copy_dates copies date-related tags."""
        source = tmp_path / "source.mp4"
        dest = tmp_path / "dest.mp4"
        source.touch()
        dest.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout="1 image files updated",
            stderr="",
        )

        result = processor.copy_dates(source, dest)

        assert result is True
        call_args = mock_runner.run.call_args[0][0]
        assert "-CreateDate" in call_args
        assert "-ModifyDate" in call_args

    def test_verify_critical_tags_all_match(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        sample_metadata: dict,
        tmp_path: Path,
    ) -> None:
        """Test verify_critical_tags when all tags match."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([sample_metadata]),
            stderr="",
        )

        result = processor.verify_critical_tags(original, converted)

        assert result.all_matched is True
        assert result.tag_results["CreateDate"] is True
        assert result.tag_results["GPSLatitude"] is True

    def test_verify_critical_tags_mismatch(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        sample_metadata: dict,
        tmp_path: Path,
    ) -> None:
        """Test verify_critical_tags when tags don't match."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        original_meta = sample_metadata.copy()
        converted_meta = sample_metadata.copy()
        converted_meta["Composite:GPSLatitude"] = 0.0  # Different value

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([original_meta]), ""),
            CommandResult(0, json.dumps([converted_meta]), ""),
        ]

        result = processor.verify_critical_tags(original, converted)

        assert result.all_matched is False
        assert result.tag_results["GPSLatitude"] is False

    def test_verify_critical_tags_missing_in_dest(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        sample_metadata: dict,
        tmp_path: Path,
    ) -> None:
        """Test verify_critical_tags when tag missing in destination."""
        original = tmp_path / "original.mp4"
        converted = tmp_path / "converted.mp4"
        original.touch()
        converted.touch()

        original_meta = sample_metadata.copy()
        converted_meta = {"SourceFile": "/converted.mp4"}  # No GPS data

        mock_runner.run.side_effect = [
            CommandResult(0, json.dumps([original_meta]), ""),
            CommandResult(0, json.dumps([converted_meta]), ""),
        ]

        result = processor.verify_critical_tags(original, converted)

        assert result.all_matched is False
        assert "GPSLatitude" in result.missing_in_dest

    def test_set_tag_success(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful set_tag operation."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout="1 image files updated",
            stderr="",
        )

        result = processor.set_tag(video_file, "CreateDate", "2024:01:15 10:00:00")

        assert result is True
        call_args = mock_runner.run.call_args[0][0]
        assert "-CreateDate=2024:01:15 10:00:00" in call_args

    def test_set_tag_file_not_found(self, processor: MetadataProcessor) -> None:
        """Test set_tag raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            processor.set_tag(Path("/nonexistent.mp4"), "CreateDate", "2024:01:15")

    def test_batch_copy_all_success(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful batch_copy_all operation."""
        pairs = []
        for i in range(3):
            source = tmp_path / f"source{i}.mp4"
            dest = tmp_path / f"dest{i}.mp4"
            source.touch()
            dest.touch()
            pairs.append((source, dest))

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout="1 image files updated",
            stderr="",
        )

        results = processor.batch_copy_all(pairs)

        assert len(results) == 3
        assert all(results.values())

    def test_batch_copy_all_partial_failure(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test batch_copy_all handles partial failures."""
        source1 = tmp_path / "source1.mp4"
        dest1 = tmp_path / "dest1.mp4"
        source1.touch()
        dest1.touch()

        source2 = tmp_path / "source2.mp4"
        dest2 = tmp_path / "dest2.mp4"
        source2.touch()
        dest2.touch()

        # First succeeds, second fails
        mock_runner.run.side_effect = [
            CommandResult(0, "1 image files updated", ""),
            CommandResult(1, "", "Error"),
        ]

        results = processor.batch_copy_all([(source1, dest1), (source2, dest2)])

        assert results[dest1] is True
        assert results[dest2] is False


class TestMetadataProcessorGPSParsing:
    """Tests for GPS coordinate parsing."""

    @pytest.fixture
    def mock_runner(self) -> MagicMock:
        """Create a mock CommandRunner."""
        runner = MagicMock(spec=CommandRunner)
        runner.check_command_exists.return_value = True
        return runner

    @pytest.fixture
    def processor(self, mock_runner: MagicMock) -> MetadataProcessor:
        """Create a MetadataProcessor with mock runner."""
        return MetadataProcessor(mock_runner)

    def test_parse_dms_format(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test parsing DMS format GPS coordinates."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        metadata = {
            "Composite:GPSLatitude": "37 deg 46' 30.00\" N",
            "Composite:GPSLongitude": "122 deg 25' 10.00\" W",
        }

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        gps = processor.extract_gps(video_file)

        assert gps is not None
        # 37 + 46/60 + 30/3600 ≈ 37.775
        assert gps.latitude == pytest.approx(37.775, rel=0.001)
        # -(122 + 25/60 + 10/3600) ≈ -122.4194
        assert gps.longitude == pytest.approx(-122.4194, rel=0.001)

    def test_parse_decimal_format(
        self,
        processor: MetadataProcessor,
        mock_runner: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test parsing decimal format GPS coordinates."""
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        metadata = {
            "Composite:GPSLatitude": 37.7749,
            "Composite:GPSLongitude": -122.4194,
        }

        mock_runner.run.return_value = CommandResult(
            returncode=0,
            stdout=json.dumps([metadata]),
            stderr="",
        )

        gps = processor.extract_gps(video_file)

        assert gps is not None
        assert gps.latitude == pytest.approx(37.7749)
        assert gps.longitude == pytest.approx(-122.4194)


class TestMetadataProcessorValueMatching:
    """Tests for value matching logic."""

    @pytest.fixture
    def processor(self) -> MetadataProcessor:
        """Create a MetadataProcessor."""
        return MetadataProcessor()

    def test_match_identical_strings(self, processor: MetadataProcessor) -> None:
        """Test matching identical strings."""
        assert processor._values_match("test", "test") is True

    def test_match_different_case(self, processor: MetadataProcessor) -> None:
        """Test matching strings with different case."""
        assert processor._values_match("Test", "test") is True

    def test_match_with_whitespace(self, processor: MetadataProcessor) -> None:
        """Test matching strings with whitespace differences."""
        assert processor._values_match("test ", " test") is True

    def test_match_integers(self, processor: MetadataProcessor) -> None:
        """Test matching integers."""
        assert processor._values_match(100, 100) is True
        assert processor._values_match(100, 101) is False

    def test_match_floats_exact(self, processor: MetadataProcessor) -> None:
        """Test matching exact floats."""
        assert processor._values_match(1.5, 1.5) is True

    def test_match_floats_tolerance(self, processor: MetadataProcessor) -> None:
        """Test matching floats within tolerance."""
        assert processor._values_match(1.00001, 1.00002) is True

    def test_match_floats_outside_tolerance(self, processor: MetadataProcessor) -> None:
        """Test non-matching floats outside tolerance."""
        assert processor._values_match(1.0, 1.001) is False

    def test_match_none_values(self, processor: MetadataProcessor) -> None:
        """Test matching None values."""
        assert processor._values_match(None, None) is True
        assert processor._values_match(None, "test") is False
        assert processor._values_match("test", None) is False
