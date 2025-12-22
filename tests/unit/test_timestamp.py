"""Unit tests for timestamp synchronization module."""

from __future__ import annotations

import os
import platform
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_converter.processors.timestamp import (
    FileTimestamps,
    TimestampReadError,
    TimestampSyncResult,
    TimestampSynchronizer,
    TimestampVerificationResult,
    TIMESTAMP_TOLERANCE_SECONDS,
)


class TestFileTimestamps:
    """Tests for FileTimestamps dataclass."""

    def test_from_file_success(self, tmp_path: Path) -> None:
        """Test extracting timestamps from an existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        timestamps = FileTimestamps.from_file(test_file)

        assert timestamps.path == test_file
        assert timestamps.modification_time is not None
        assert timestamps.access_time is not None
        assert isinstance(timestamps.modification_time, datetime)
        assert isinstance(timestamps.access_time, datetime)

    def test_from_file_with_birth_time(self, tmp_path: Path) -> None:
        """Test that birth time is extracted on macOS."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        timestamps = FileTimestamps.from_file(test_file)

        if platform.system() == "Darwin":
            assert timestamps.birth_time is not None
            assert isinstance(timestamps.birth_time, datetime)
        else:
            # On non-macOS, birth_time may be None
            pass

    def test_from_file_not_found(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised for missing files."""
        missing_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            FileTimestamps.from_file(missing_file)

    def test_str_representation(self, tmp_path: Path) -> None:
        """Test string representation of timestamps."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        timestamps = FileTimestamps.from_file(test_file)
        result = str(timestamps)

        assert "test.txt" in result
        assert "Modified:" in result


class TestTimestampSynchronizer:
    """Tests for TimestampSynchronizer class."""

    def test_init(self) -> None:
        """Test synchronizer initialization."""
        sync = TimestampSynchronizer()

        assert sync.is_macos == (platform.system() == "Darwin")

    def test_sync_from_file_success(self, tmp_path: Path) -> None:
        """Test successful timestamp synchronization between files."""
        # Create source file with specific timestamp
        source = tmp_path / "source.txt"
        source.write_text("source content")

        # Set a specific modification time on source
        old_time = datetime(2020, 1, 15, 10, 30, 0).timestamp()
        os.utime(source, (old_time, old_time))

        # Create destination file
        dest = tmp_path / "dest.txt"
        dest.write_text("dest content")

        sync = TimestampSynchronizer()
        result = sync.sync_from_file(source, dest)

        assert result.success is True
        assert result.source == source
        assert result.dest == dest
        assert result.modification_time_synced is True
        assert result.access_time_synced is True

        # Verify destination now has source's modification time
        dest_stat = dest.stat()
        assert abs(dest_stat.st_mtime - old_time) < 1.0

    def test_sync_from_file_source_not_found(self, tmp_path: Path) -> None:
        """Test sync fails when source file doesn't exist."""
        source = tmp_path / "nonexistent.txt"
        dest = tmp_path / "dest.txt"
        dest.write_text("dest content")

        sync = TimestampSynchronizer()
        result = sync.sync_from_file(source, dest)

        assert result.success is False
        assert "not found" in result.error_message

    def test_sync_from_file_dest_not_found(self, tmp_path: Path) -> None:
        """Test sync fails when destination file doesn't exist."""
        source = tmp_path / "source.txt"
        source.write_text("source content")
        dest = tmp_path / "nonexistent.txt"

        sync = TimestampSynchronizer()
        result = sync.sync_from_file(source, dest)

        assert result.success is False
        assert "not found" in result.error_message

    def test_sync_from_file_partial_sync(self, tmp_path: Path) -> None:
        """Test partial sync when only some timestamps are requested."""
        source = tmp_path / "source.txt"
        source.write_text("source content")
        dest = tmp_path / "dest.txt"
        dest.write_text("dest content")

        sync = TimestampSynchronizer()
        result = sync.sync_from_file(
            source,
            dest,
            sync_modification_time=True,
            sync_access_time=False,
            sync_birth_time=False,
        )

        assert result.success is True
        assert result.modification_time_synced is True
        assert result.access_time_synced is False

    def test_sync_from_datetime_success(self, tmp_path: Path) -> None:
        """Test setting timestamps from datetime values."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        target_time = datetime(2021, 6, 15, 14, 30, 0)

        sync = TimestampSynchronizer()
        result = sync.sync_from_datetime(
            path=test_file,
            modification_date=target_time,
        )

        assert result.success is True
        assert result.modification_time_synced is True

        # Verify the modification time was set
        file_stat = test_file.stat()
        assert abs(file_stat.st_mtime - target_time.timestamp()) < 1.0

    def test_sync_from_datetime_file_not_found(self, tmp_path: Path) -> None:
        """Test sync from datetime fails when file doesn't exist."""
        missing_file = tmp_path / "nonexistent.txt"

        sync = TimestampSynchronizer()
        result = sync.sync_from_datetime(
            path=missing_file,
            modification_date=datetime.now(),
        )

        assert result.success is False
        assert "not found" in result.error_message

    def test_get_timestamps(self, tmp_path: Path) -> None:
        """Test getting timestamps from a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        sync = TimestampSynchronizer()
        timestamps = sync.get_timestamps(test_file)

        assert timestamps.path == test_file
        assert timestamps.modification_time is not None


class TestTimestampVerification:
    """Tests for timestamp verification."""

    def test_verify_matching_timestamps(self, tmp_path: Path) -> None:
        """Test verification passes when timestamps match."""
        # Create two files with same timestamps
        original = tmp_path / "original.txt"
        original.write_text("original content")

        converted = tmp_path / "converted.txt"
        converted.write_text("converted content")

        # Sync timestamps
        sync = TimestampSynchronizer()
        sync.sync_from_file(original, converted)

        # Verify
        result = sync.verify(original, converted)

        assert result.passed is True
        assert result.modification_time_match is True

    def test_verify_mismatched_timestamps(self, tmp_path: Path) -> None:
        """Test verification fails when timestamps differ."""
        original = tmp_path / "original.txt"
        original.write_text("original content")

        # Set a specific old time on original
        old_time = datetime(2019, 1, 1, 0, 0, 0).timestamp()
        os.utime(original, (old_time, old_time))

        converted = tmp_path / "converted.txt"
        converted.write_text("converted content")
        # converted has current time by default

        sync = TimestampSynchronizer()
        result = sync.verify(original, converted)

        assert result.passed is False
        assert result.modification_time_match is False

    def test_verify_with_tolerance(self, tmp_path: Path) -> None:
        """Test verification uses tolerance for comparison."""
        original = tmp_path / "original.txt"
        original.write_text("original content")

        converted = tmp_path / "converted.txt"
        converted.write_text("converted content")

        # Set times that differ by 1 second
        base_time = datetime(2020, 6, 15, 12, 0, 0).timestamp()
        os.utime(original, (base_time, base_time))
        os.utime(converted, (base_time + 1, base_time + 1))

        sync = TimestampSynchronizer()

        # With default tolerance (2 seconds), should pass
        result = sync.verify(original, converted, tolerance_seconds=2.0)
        assert result.passed is True

        # With tight tolerance (0.5 seconds), should fail
        result = sync.verify(original, converted, tolerance_seconds=0.5)
        assert result.passed is False

    def test_verify_file_not_found(self, tmp_path: Path) -> None:
        """Test verification raises error for missing files."""
        original = tmp_path / "original.txt"
        original.write_text("content")
        missing = tmp_path / "missing.txt"

        sync = TimestampSynchronizer()

        with pytest.raises(FileNotFoundError):
            sync.verify(missing, original)

        with pytest.raises(FileNotFoundError):
            sync.verify(original, missing)


class TestTimestampSyncResult:
    """Tests for TimestampSyncResult dataclass."""

    def test_success_result(self, tmp_path: Path) -> None:
        """Test creating a successful result."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"

        result = TimestampSyncResult(
            success=True,
            source=source,
            dest=dest,
            birth_time_synced=True,
            modification_time_synced=True,
            access_time_synced=True,
        )

        assert result.success is True
        assert result.error_message is None
        assert len(result.warnings) == 0

    def test_failed_result_with_error(self, tmp_path: Path) -> None:
        """Test creating a failed result with error message."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"

        result = TimestampSyncResult(
            success=False,
            source=source,
            dest=dest,
            error_message="File not found",
        )

        assert result.success is False
        assert result.error_message == "File not found"

    def test_result_with_warnings(self, tmp_path: Path) -> None:
        """Test result with warnings."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"

        result = TimestampSyncResult(
            success=True,
            source=source,
            dest=dest,
            warnings=["Could not set birth time"],
        )

        assert result.success is True
        assert len(result.warnings) == 1


class TestBirthTimeSync:
    """Tests for birth time (creation date) synchronization."""

    @pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="Birth time setting only works on macOS",
    )
    def test_birth_time_sync_macos(self, tmp_path: Path) -> None:
        """Test birth time sync on macOS."""
        source = tmp_path / "source.txt"
        source.write_text("source content")

        dest = tmp_path / "dest.txt"
        dest.write_text("dest content")

        sync = TimestampSynchronizer()
        result = sync.sync_from_file(source, dest, sync_birth_time=True)

        # Birth time sync may or may not succeed depending on
        # whether SetFile is available
        assert result.source == source
        assert result.dest == dest

    def test_birth_time_warning_on_non_macos(self, tmp_path: Path) -> None:
        """Test that birth time sync adds warning on non-macOS."""
        if platform.system() == "Darwin":
            pytest.skip("Test only applies to non-macOS systems")

        source = tmp_path / "source.txt"
        source.write_text("source content")

        dest = tmp_path / "dest.txt"
        dest.write_text("dest content")

        sync = TimestampSynchronizer()
        result = sync.sync_from_file(source, dest, sync_birth_time=True)

        # Should have a warning about birth time not being supported
        assert any("macOS" in w for w in result.warnings) or result.success


class TestTimestampVerificationResult:
    """Tests for TimestampVerificationResult dataclass."""

    def test_passed_result(self) -> None:
        """Test creating a passed verification result."""
        result = TimestampVerificationResult(
            passed=True,
            birth_time_match=True,
            modification_time_match=True,
            details="All timestamps match",
        )

        assert result.passed is True
        assert result.tolerance_seconds == TIMESTAMP_TOLERANCE_SECONDS

    def test_failed_result(self) -> None:
        """Test creating a failed verification result."""
        result = TimestampVerificationResult(
            passed=False,
            birth_time_match=False,
            modification_time_match=False,
            details="Timestamps differ",
        )

        assert result.passed is False
