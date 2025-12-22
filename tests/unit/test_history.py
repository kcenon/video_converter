"""Unit tests for conversion history module."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from video_converter.core.history import (
    ConversionHistory,
    ConversionRecord,
    HistoryCorruptedError,
    HistoryStatistics,
    get_history,
    reset_history,
)


class TestConversionRecord:
    """Tests for ConversionRecord dataclass."""

    def test_successful_record(self) -> None:
        """Test creating a successful conversion record."""
        record = ConversionRecord(
            id="abc123",
            source_path="/videos/test.mov",
            output_path="/videos/test_h265.mp4",
            source_codec="h264",
            output_codec="hevc",
            source_size=1000000,
            output_size=400000,
            converted_at="2025-01-01T10:00:00",
            success=True,
        )

        assert record.id == "abc123"
        assert record.success is True
        assert record.error_message is None

    def test_failed_record(self) -> None:
        """Test creating a failed conversion record."""
        record = ConversionRecord(
            id="def456",
            source_path="/videos/test.mov",
            output_path=None,
            source_codec="h264",
            output_codec="hevc",
            source_size=1000000,
            output_size=None,
            converted_at="2025-01-01T10:00:00",
            success=False,
            error_message="Encoder failed",
        )

        assert record.success is False
        assert record.error_message == "Encoder failed"
        assert record.output_path is None

    def test_size_saved_success(self) -> None:
        """Test size_saved calculation for successful conversion."""
        record = ConversionRecord(
            id="abc123",
            source_path="/videos/test.mov",
            output_path="/videos/test_h265.mp4",
            source_codec="h264",
            output_codec="hevc",
            source_size=1000000,
            output_size=400000,
            converted_at="2025-01-01T10:00:00",
            success=True,
        )

        assert record.size_saved == 600000

    def test_size_saved_failed(self) -> None:
        """Test size_saved returns 0 for failed conversion."""
        record = ConversionRecord(
            id="abc123",
            source_path="/videos/test.mov",
            output_path=None,
            source_codec="h264",
            output_codec="hevc",
            source_size=1000000,
            output_size=None,
            converted_at="2025-01-01T10:00:00",
            success=False,
        )

        assert record.size_saved == 0

    def test_size_saved_increased(self) -> None:
        """Test size_saved returns 0 when output is larger."""
        record = ConversionRecord(
            id="abc123",
            source_path="/videos/test.mov",
            output_path="/videos/test_h265.mp4",
            source_codec="h264",
            output_codec="hevc",
            source_size=400000,
            output_size=500000,
            converted_at="2025-01-01T10:00:00",
            success=True,
        )

        assert record.size_saved == 0

    def test_compression_ratio(self) -> None:
        """Test compression ratio calculation."""
        record = ConversionRecord(
            id="abc123",
            source_path="/videos/test.mov",
            output_path="/videos/test_h265.mp4",
            source_codec="h264",
            output_codec="hevc",
            source_size=1000000,
            output_size=400000,
            converted_at="2025-01-01T10:00:00",
            success=True,
        )

        assert record.compression_ratio == pytest.approx(0.6)

    def test_compression_ratio_failed(self) -> None:
        """Test compression ratio returns 0 for failed conversion."""
        record = ConversionRecord(
            id="abc123",
            source_path="/videos/test.mov",
            output_path=None,
            source_codec="h264",
            output_codec="hevc",
            source_size=1000000,
            output_size=None,
            converted_at="2025-01-01T10:00:00",
            success=False,
        )

        assert record.compression_ratio == 0.0

    def test_compression_ratio_zero_source(self) -> None:
        """Test compression ratio handles zero source size."""
        record = ConversionRecord(
            id="abc123",
            source_path="/videos/test.mov",
            output_path="/videos/test_h265.mp4",
            source_codec="h264",
            output_codec="hevc",
            source_size=0,
            output_size=100,
            converted_at="2025-01-01T10:00:00",
            success=True,
        )

        assert record.compression_ratio == 0.0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        record = ConversionRecord(
            id="abc123",
            source_path="/videos/test.mov",
            output_path="/videos/test_h265.mp4",
            source_codec="h264",
            output_codec="hevc",
            source_size=1000000,
            output_size=400000,
            converted_at="2025-01-01T10:00:00",
            success=True,
        )

        data = record.to_dict()

        assert data["id"] == "abc123"
        assert data["source_path"] == "/videos/test.mov"
        assert data["output_path"] == "/videos/test_h265.mp4"
        assert data["source_codec"] == "h264"
        assert data["output_codec"] == "hevc"
        assert data["source_size"] == 1000000
        assert data["output_size"] == 400000
        assert data["success"] is True

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "id": "abc123",
            "source_path": "/videos/test.mov",
            "output_path": "/videos/test_h265.mp4",
            "source_codec": "h264",
            "output_codec": "hevc",
            "source_size": 1000000,
            "output_size": 400000,
            "converted_at": "2025-01-01T10:00:00",
            "success": True,
        }

        record = ConversionRecord.from_dict(data)

        assert record.id == "abc123"
        assert record.source_size == 1000000
        assert record.success is True

    def test_from_dict_with_error(self) -> None:
        """Test creation from dictionary with error message."""
        data = {
            "id": "abc123",
            "source_path": "/videos/test.mov",
            "output_path": None,
            "source_codec": "h264",
            "output_codec": "hevc",
            "source_size": 1000000,
            "output_size": None,
            "converted_at": "2025-01-01T10:00:00",
            "success": False,
            "error_message": "Encoder error",
        }

        record = ConversionRecord.from_dict(data)

        assert record.success is False
        assert record.error_message == "Encoder error"


class TestHistoryStatistics:
    """Tests for HistoryStatistics dataclass."""

    def test_default_values(self) -> None:
        """Test default statistics values."""
        stats = HistoryStatistics()

        assert stats.total_converted == 0
        assert stats.total_failed == 0
        assert stats.total_source_bytes == 0
        assert stats.total_output_bytes == 0
        assert stats.total_saved_bytes == 0
        assert stats.first_conversion is None
        assert stats.last_conversion is None

    def test_success_rate(self) -> None:
        """Test success rate calculation."""
        stats = HistoryStatistics(
            total_converted=8,
            total_failed=2,
        )

        assert stats.success_rate == pytest.approx(0.8)

    def test_success_rate_empty(self) -> None:
        """Test success rate with no conversions."""
        stats = HistoryStatistics()

        assert stats.success_rate == 0.0

    def test_average_compression_ratio(self) -> None:
        """Test average compression ratio calculation."""
        stats = HistoryStatistics(
            total_source_bytes=1000000,
            total_output_bytes=400000,
        )

        assert stats.average_compression_ratio == pytest.approx(0.6)

    def test_average_compression_ratio_empty(self) -> None:
        """Test compression ratio with no data."""
        stats = HistoryStatistics()

        assert stats.average_compression_ratio == 0.0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        stats = HistoryStatistics(
            total_converted=10,
            total_failed=2,
            total_source_bytes=1000000,
            total_output_bytes=400000,
            total_saved_bytes=600000,
            first_conversion="2025-01-01T10:00:00",
            last_conversion="2025-01-15T10:00:00",
        )

        data = stats.to_dict()

        assert data["total_converted"] == 10
        assert data["total_failed"] == 2
        assert data["success_rate"] == pytest.approx(10 / 12)
        assert data["average_compression_ratio"] == pytest.approx(0.6)


class TestConversionHistory:
    """Tests for ConversionHistory class."""

    def test_initialization(self) -> None:
        """Test history initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            assert history.history_path == history_path
            assert history.count() == 0

    def test_initialization_creates_directory(self) -> None:
        """Test that initialization creates parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "subdir" / "history.json"
            history = ConversionHistory(history_path=history_path)

            assert history_path.parent.exists()

    def test_add_record(self) -> None:
        """Test adding a conversion record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            record = ConversionRecord(
                id="abc123",
                source_path="/videos/test.mov",
                output_path="/videos/test_h265.mp4",
                source_codec="h264",
                output_codec="hevc",
                source_size=1000000,
                output_size=400000,
                converted_at=datetime.now().isoformat(),
                success=True,
            )

            history.add_record(record)

            assert history.count() == 1
            assert history.is_converted("abc123") is True

    def test_is_converted_not_found(self) -> None:
        """Test is_converted returns False for unknown ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            assert history.is_converted("unknown") is False

    def test_is_converted_failed(self) -> None:
        """Test is_converted returns False for failed conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            record = ConversionRecord(
                id="abc123",
                source_path="/videos/test.mov",
                output_path=None,
                source_codec="h264",
                output_codec="hevc",
                source_size=1000000,
                output_size=None,
                converted_at=datetime.now().isoformat(),
                success=False,
            )

            history.add_record(record)

            assert history.is_converted("abc123") is False

    def test_get_record(self) -> None:
        """Test getting a record by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            record = ConversionRecord(
                id="abc123",
                source_path="/videos/test.mov",
                output_path="/videos/test_h265.mp4",
                source_codec="h264",
                output_codec="hevc",
                source_size=1000000,
                output_size=400000,
                converted_at=datetime.now().isoformat(),
                success=True,
            )

            history.add_record(record)
            retrieved = history.get_record("abc123")

            assert retrieved is not None
            assert retrieved.id == "abc123"

    def test_get_record_not_found(self) -> None:
        """Test getting non-existent record returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            assert history.get_record("unknown") is None

    def test_remove_record(self) -> None:
        """Test removing a record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            record = ConversionRecord(
                id="abc123",
                source_path="/videos/test.mov",
                output_path="/videos/test_h265.mp4",
                source_codec="h264",
                output_codec="hevc",
                source_size=1000000,
                output_size=400000,
                converted_at=datetime.now().isoformat(),
                success=True,
            )

            history.add_record(record)
            result = history.remove_record("abc123")

            assert result is True
            assert history.count() == 0
            assert history.get_record("abc123") is None

    def test_remove_record_not_found(self) -> None:
        """Test removing non-existent record returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            assert history.remove_record("unknown") is False

    def test_clear(self) -> None:
        """Test clearing all records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            for i in range(5):
                record = ConversionRecord(
                    id=f"id{i}",
                    source_path=f"/videos/test{i}.mov",
                    output_path=f"/videos/test{i}_h265.mp4",
                    source_codec="h264",
                    output_codec="hevc",
                    source_size=1000000,
                    output_size=400000,
                    converted_at=datetime.now().isoformat(),
                    success=True,
                )
                history.add_record(record)

            assert history.count() == 5

            history.clear()

            assert history.count() == 0

    def test_persistence(self) -> None:
        """Test that records persist across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"

            # First instance
            history1 = ConversionHistory(history_path=history_path)
            record = ConversionRecord(
                id="abc123",
                source_path="/videos/test.mov",
                output_path="/videos/test_h265.mp4",
                source_codec="h264",
                output_codec="hevc",
                source_size=1000000,
                output_size=400000,
                converted_at=datetime.now().isoformat(),
                success=True,
            )
            history1.add_record(record)

            # Second instance loads from file
            history2 = ConversionHistory(history_path=history_path)

            assert history2.count() == 1
            assert history2.is_converted("abc123") is True

    def test_load_corrupted_json(self) -> None:
        """Test loading corrupted JSON raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history_path.write_text("not valid json")

            with pytest.raises(HistoryCorruptedError):
                ConversionHistory(history_path=history_path)

    def test_load_invalid_format(self) -> None:
        """Test loading invalid format raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history_path.write_text('["array", "not", "object"]')

            with pytest.raises(HistoryCorruptedError):
                ConversionHistory(history_path=history_path)

    def test_get_statistics(self) -> None:
        """Test statistics calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            # Add successful records
            for i in range(3):
                record = ConversionRecord(
                    id=f"success{i}",
                    source_path=f"/videos/test{i}.mov",
                    output_path=f"/videos/test{i}_h265.mp4",
                    source_codec="h264",
                    output_codec="hevc",
                    source_size=1000000,
                    output_size=400000,
                    converted_at=f"2025-01-{i+1:02d}T10:00:00",
                    success=True,
                )
                history.add_record(record)

            # Add failed record
            failed = ConversionRecord(
                id="failed1",
                source_path="/videos/fail.mov",
                output_path=None,
                source_codec="h264",
                output_codec="hevc",
                source_size=1000000,
                output_size=None,
                converted_at="2025-01-04T10:00:00",
                success=False,
            )
            history.add_record(failed)

            stats = history.get_statistics()

            assert stats.total_converted == 3
            assert stats.total_failed == 1
            assert stats.total_source_bytes == 3000000
            assert stats.total_output_bytes == 1200000
            assert stats.total_saved_bytes == 1800000
            assert stats.first_conversion == "2025-01-01T10:00:00"
            assert stats.last_conversion == "2025-01-03T10:00:00"

    def test_get_all_records(self) -> None:
        """Test getting all records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            for i in range(3):
                record = ConversionRecord(
                    id=f"id{i}",
                    source_path=f"/videos/test{i}.mov",
                    output_path=f"/videos/test{i}_h265.mp4",
                    source_codec="h264",
                    output_codec="hevc",
                    source_size=1000000,
                    output_size=400000,
                    converted_at=datetime.now().isoformat(),
                    success=True,
                )
                history.add_record(record)

            records = history.get_all_records()

            assert len(records) == 3

    def test_get_failed_records(self) -> None:
        """Test getting only failed records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            # Add mixed records
            for i in range(2):
                record = ConversionRecord(
                    id=f"success{i}",
                    source_path=f"/videos/test{i}.mov",
                    output_path=f"/videos/test{i}_h265.mp4",
                    source_codec="h264",
                    output_codec="hevc",
                    source_size=1000000,
                    output_size=400000,
                    converted_at=datetime.now().isoformat(),
                    success=True,
                )
                history.add_record(record)

            for i in range(3):
                record = ConversionRecord(
                    id=f"failed{i}",
                    source_path=f"/videos/fail{i}.mov",
                    output_path=None,
                    source_codec="h264",
                    output_codec="hevc",
                    source_size=1000000,
                    output_size=None,
                    converted_at=datetime.now().isoformat(),
                    success=False,
                )
                history.add_record(record)

            failed = history.get_failed_records()

            assert len(failed) == 3
            assert all(not r.success for r in failed)

    def test_get_successful_records(self) -> None:
        """Test getting only successful records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history = ConversionHistory(history_path=history_path)

            # Add mixed records
            for i in range(3):
                record = ConversionRecord(
                    id=f"success{i}",
                    source_path=f"/videos/test{i}.mov",
                    output_path=f"/videos/test{i}_h265.mp4",
                    source_codec="h264",
                    output_codec="hevc",
                    source_size=1000000,
                    output_size=400000,
                    converted_at=datetime.now().isoformat(),
                    success=True,
                )
                history.add_record(record)

            for i in range(2):
                record = ConversionRecord(
                    id=f"failed{i}",
                    source_path=f"/videos/fail{i}.mov",
                    output_path=None,
                    source_codec="h264",
                    output_codec="hevc",
                    source_size=1000000,
                    output_size=None,
                    converted_at=datetime.now().isoformat(),
                    success=False,
                )
                history.add_record(record)

            successful = history.get_successful_records()

            assert len(successful) == 3
            assert all(r.success for r in successful)

    def test_export_to_json(self) -> None:
        """Test exporting history to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            export_path = Path(tmpdir) / "export.json"
            history = ConversionHistory(history_path=history_path)

            record = ConversionRecord(
                id="abc123",
                source_path="/videos/test.mov",
                output_path="/videos/test_h265.mp4",
                source_codec="h264",
                output_codec="hevc",
                source_size=1000000,
                output_size=400000,
                converted_at=datetime.now().isoformat(),
                success=True,
            )
            history.add_record(record)

            history.export_to_json(export_path)

            assert export_path.exists()

            with open(export_path, encoding="utf-8") as f:
                data = json.load(f)

            assert "exported_at" in data
            assert "statistics" in data
            assert "records" in data
            assert len(data["records"]) == 1

    def test_export_to_csv(self) -> None:
        """Test exporting history to CSV file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            export_path = Path(tmpdir) / "export.csv"
            history = ConversionHistory(history_path=history_path)

            record = ConversionRecord(
                id="abc123",
                source_path="/videos/test.mov",
                output_path="/videos/test_h265.mp4",
                source_codec="h264",
                output_codec="hevc",
                source_size=1000000,
                output_size=400000,
                converted_at=datetime.now().isoformat(),
                success=True,
            )
            history.add_record(record)

            history.export_to_csv(export_path)

            assert export_path.exists()

            content = export_path.read_text()
            assert "id" in content
            assert "source_path" in content
            assert "abc123" in content

    def test_compute_file_hash(self) -> None:
        """Test file hash computation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.bin"
            test_file.write_bytes(b"test content" * 1000)

            hash1 = ConversionHistory.compute_file_hash(test_file)

            # Hash should be 16 characters
            assert len(hash1) == 16

            # Same file should produce same hash
            hash2 = ConversionHistory.compute_file_hash(test_file)
            assert hash1 == hash2

    def test_compute_file_hash_different_files(self) -> None:
        """Test that different files produce different hashes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "test1.bin"
            file2 = Path(tmpdir) / "test2.bin"

            file1.write_bytes(b"content one" * 1000)
            file2.write_bytes(b"content two" * 1000)

            hash1 = ConversionHistory.compute_file_hash(file1)
            hash2 = ConversionHistory.compute_file_hash(file2)

            assert hash1 != hash2

    def test_compute_file_hash_large_file(self) -> None:
        """Test hash computation for large files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            large_file = Path(tmpdir) / "large.bin"

            # Create 3MB file
            with open(large_file, "wb") as f:
                f.write(b"x" * (3 * 1024 * 1024))

            file_hash = ConversionHistory.compute_file_hash(large_file)

            assert len(file_hash) == 16


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    def test_get_history_singleton(self) -> None:
        """Test get_history returns singleton."""
        reset_history()

        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"

            history1 = get_history(history_path)
            history2 = get_history()  # Should return same instance

            assert history1 is history2

            reset_history()

    def test_reset_history(self) -> None:
        """Test reset_history clears singleton."""
        reset_history()

        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"

            history1 = get_history(history_path)
            reset_history()
            history2 = get_history(history_path)

            assert history1 is not history2

            reset_history()
