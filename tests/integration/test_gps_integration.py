"""Integration tests for GPS handling with real video files.

This test module requires real video files with GPS data.
Place test files in tests/fixtures/gps/ directory.

Usage:
    pytest tests/integration/test_gps_integration.py -v

Required test files:
    - tests/fixtures/gps/iphone_video.mov    (iPhone video with GPS)
    - tests/fixtures/gps/android_video.mp4   (Android video with GPS)
    - tests/fixtures/gps/no_gps_video.mp4    (Video without GPS)
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from video_converter.processors.gps import GPSCoordinates, GPSHandler
from video_converter.processors.metadata import MetadataProcessor


# Skip all tests if exiftool is not available
pytestmark = pytest.mark.skipif(
    shutil.which("exiftool") is None,
    reason="exiftool not installed",
)


class TestGPSIntegration:
    """Integration tests for GPS handling."""

    @pytest.fixture
    def handler(self) -> GPSHandler:
        """Create a GPSHandler instance."""
        return GPSHandler()

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Get the fixtures directory path."""
        return Path(__file__).parent.parent / "fixtures" / "gps"

    def test_exiftool_available(self, handler: GPSHandler) -> None:
        """Test that exiftool is available."""
        assert handler._processor.is_available()

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "fixtures" / "gps").exists(),
        reason="GPS fixtures directory not found",
    )
    def test_extract_iphone_gps(self, handler: GPSHandler, fixtures_dir: Path) -> None:
        """Test GPS extraction from iPhone video."""
        video_path = fixtures_dir / "iphone_video.mov"
        if not video_path.exists():
            pytest.skip(f"Test file not found: {video_path}")

        coords = handler.extract(video_path)

        assert coords is not None
        assert -90 <= coords.latitude <= 90
        assert -180 <= coords.longitude <= 180
        print(f"\niPhone GPS: {coords}")

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "fixtures" / "gps").exists(),
        reason="GPS fixtures directory not found",
    )
    def test_extract_android_gps(self, handler: GPSHandler, fixtures_dir: Path) -> None:
        """Test GPS extraction from Android video."""
        video_path = fixtures_dir / "android_video.mp4"
        if not video_path.exists():
            pytest.skip(f"Test file not found: {video_path}")

        coords = handler.extract(video_path)

        assert coords is not None
        assert -90 <= coords.latitude <= 90
        assert -180 <= coords.longitude <= 180
        print(f"\nAndroid GPS: {coords}")

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "fixtures" / "gps").exists(),
        reason="GPS fixtures directory not found",
    )
    def test_no_gps_video(self, handler: GPSHandler, fixtures_dir: Path) -> None:
        """Test GPS extraction from video without GPS."""
        video_path = fixtures_dir / "no_gps_video.mp4"
        if not video_path.exists():
            pytest.skip(f"Test file not found: {video_path}")

        coords = handler.extract(video_path)
        assert coords is None

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "fixtures" / "gps").exists(),
        reason="GPS fixtures directory not found",
    )
    def test_gps_copy_and_verify(
        self, handler: GPSHandler, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """Test GPS copy and verification."""
        source_path = fixtures_dir / "iphone_video.mov"
        if not source_path.exists():
            pytest.skip(f"Test file not found: {source_path}")

        # Create a copy without GPS
        dest_path = tmp_path / "copy.mov"
        shutil.copy(source_path, dest_path)

        # Extract original GPS
        original_gps = handler.extract(source_path)
        assert original_gps is not None

        # Copy GPS
        success = handler.copy(source_path, dest_path)
        assert success

        # Verify GPS was copied
        result = handler.verify(source_path, dest_path)
        assert result.passed
        print(f"\nVerification: {result.details}")


class TestGPSFormatConversion:
    """Test GPS format conversions with real coordinates."""

    def test_round_trip_quicktime(self) -> None:
        """Test QuickTime format round-trip conversion."""
        original = GPSCoordinates(
            latitude=37.774929,
            longitude=-122.419416,
            altitude=10.5,
        )

        # Convert to QuickTime format
        qt_string = original.to_quicktime()
        print(f"\nQuickTime format: {qt_string}")

        # Parse back
        parsed = GPSCoordinates.from_quicktime(qt_string)

        assert parsed is not None
        assert original.matches(parsed)
        assert parsed.altitude == pytest.approx(original.altitude, rel=0.01)

    def test_round_trip_xmp(self) -> None:
        """Test XMP format round-trip conversion."""
        original = GPSCoordinates(
            latitude=37.774929,
            longitude=-122.419416,
        )

        # Convert to XMP format
        lat_xmp, lon_xmp = original.to_xmp()
        print(f"\nXMP format: {lat_xmp}, {lon_xmp}")

        # Parse back
        parsed = GPSCoordinates.from_xmp(lat_xmp, lon_xmp)

        assert parsed is not None
        assert original.matches(parsed)

    def test_distance_calculation(self) -> None:
        """Test distance calculation between known locations."""
        # San Francisco City Hall
        sf = GPSCoordinates(latitude=37.7793, longitude=-122.4193)
        # Oakland City Hall
        oakland = GPSCoordinates(latitude=37.8044, longitude=-122.2712)

        distance = sf.distance_to(oakland)
        # Expected: ~13.5 km
        assert 13000 < distance < 14000
        print(f"\nDistance SF to Oakland: {distance / 1000:.2f} km")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
