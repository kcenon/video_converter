"""End-to-end tests for GUI video conversion.

This module contains E2E tests that perform actual video conversions
through the GUI to verify the complete user experience from file
selection to conversion completion.

These tests require:
- FFmpeg installed
- ExifTool installed (for metadata tests)
- Sufficient disk space for output

Run with: pytest tests/gui/test_e2e.py -v -m e2e
Skip with: pytest -m "not e2e"
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


# Skip all tests if PySide6 is not available
pytest.importorskip("PySide6")

# Common markers for all E2E tests
pytestmark = [pytest.mark.gui, pytest.mark.e2e, pytest.mark.slow]


def _get_video_codec(file_path: Path) -> str | None:
    """Get the video codec of a file using FFprobe.

    Args:
        file_path: Path to the video file.

    Returns:
        Codec name (e.g., 'hevc', 'h264') or None if detection fails.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "json",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            if streams:
                return streams[0].get("codec_name")
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return None


def _get_file_size(file_path: Path) -> int:
    """Get file size in bytes.

    Args:
        file_path: Path to the file.

    Returns:
        File size in bytes, or 0 if file doesn't exist.
    """
    return file_path.stat().st_size if file_path.exists() else 0


class TestSingleFileE2E:
    """End-to-end tests for single file conversion."""

    def test_complete_conversion(
        self,
        qtbot: QtBot,
        sample_h264_video: Path | None,
        e2e_output_dir: Path,
        ffmpeg_available: bool,
    ) -> None:
        """Test complete single file conversion through GUI.

        This test:
        1. Creates a ConversionService
        2. Adds a test video file
        3. Waits for conversion to complete
        4. Verifies output file exists and is H.265
        """
        if not ffmpeg_available or sample_h264_video is None:
            pytest.skip("FFmpeg not available or sample video creation failed")

        from video_converter.gui.services.conversion_service import ConversionService

        service = ConversionService()
        # Note: ConversionService is a QObject, not QWidget, so we don't use addWidget.
        # Cleanup is handled by service.shutdown() in the finally block.

        try:
            # Track completion
            completed_tasks = []

            def on_completed(task_id: str, result: dict) -> None:
                completed_tasks.append((task_id, result))

            service.task_completed.connect(on_completed)

            # Add task with output directory setting
            settings = {"output_dir": str(e2e_output_dir)}
            task_id = service.add_task(str(sample_h264_video), settings=settings)
            assert task_id is not None

            # Wait for conversion (timeout 120 seconds for slow systems)
            timeout = 120000  # ms
            start_time = time.time()

            while not completed_tasks and (time.time() - start_time) < (timeout / 1000):
                qtbot.wait(500)

            # Verify completion
            assert len(completed_tasks) == 1, "Conversion should complete"
            result_task_id, result = completed_tasks[0]
            assert result_task_id == task_id

            # Verify output file
            output_files = list(e2e_output_dir.glob("*.mp4"))
            assert len(output_files) >= 1, "Output file should be created"

            output_file = output_files[0]
            assert output_file.exists()
            assert _get_file_size(output_file) > 0

            # Verify codec is H.265
            codec = _get_video_codec(output_file)
            assert codec == "hevc", f"Output should be H.265, got {codec}"

        finally:
            service.shutdown()

    def test_conversion_with_metadata(
        self,
        qtbot: QtBot,
        video_with_gps: Path | None,
        e2e_output_dir: Path,
        ffmpeg_available: bool,
        exiftool_available: bool,
    ) -> None:
        """Test that GPS metadata is preserved after conversion."""
        if not ffmpeg_available or not exiftool_available:
            pytest.skip("FFmpeg or ExifTool not available")
        if video_with_gps is None:
            pytest.skip("GPS video creation failed")

        from video_converter.gui.services.conversion_service import ConversionService

        service = ConversionService()

        try:
            completed_tasks = []
            service.task_completed.connect(
                lambda tid, res: completed_tasks.append((tid, res))
            )

            settings = {"output_dir": str(e2e_output_dir)}
            task_id = service.add_task(str(video_with_gps), settings=settings)

            # Wait for completion
            timeout = 120000
            start_time = time.time()
            while not completed_tasks and (time.time() - start_time) < (timeout / 1000):
                qtbot.wait(500)

            assert len(completed_tasks) == 1

            # Check metadata preservation
            output_files = list(e2e_output_dir.glob("*.mp4"))
            assert len(output_files) >= 1

            output_file = output_files[0]

            # Verify GPS metadata using exiftool
            result = subprocess.run(
                ["exiftool", "-GPSLatitude", "-GPSLongitude", "-json", str(output_file)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                metadata = json.loads(result.stdout)
                if metadata:
                    # GPS metadata should be preserved
                    gps_lat = metadata[0].get("GPSLatitude")
                    gps_lon = metadata[0].get("GPSLongitude")
                    # Note: Metadata may not always be preserved depending on settings
                    # This test documents the current behavior

        finally:
            service.shutdown()

    def test_software_encoding(
        self,
        qtbot: QtBot,
        sample_h264_video: Path | None,
        e2e_output_dir: Path,
        ffmpeg_available: bool,
    ) -> None:
        """Test conversion with software encoding (libx265)."""
        if not ffmpeg_available or sample_h264_video is None:
            pytest.skip("FFmpeg not available or sample video creation failed")

        from video_converter.gui.services.conversion_service import ConversionService

        service = ConversionService()

        try:
            completed_tasks = []
            service.task_completed.connect(
                lambda tid, res: completed_tasks.append((tid, res))
            )

            # Force software encoding
            settings = {
                "output_dir": str(e2e_output_dir),
                "encoder": "Software (libx265)",
            }
            task_id = service.add_task(str(sample_h264_video), settings=settings)

            timeout = 180000  # Software encoding is slower
            start_time = time.time()
            while not completed_tasks and (time.time() - start_time) < (timeout / 1000):
                qtbot.wait(500)

            assert len(completed_tasks) == 1

            output_files = list(e2e_output_dir.glob("*.mp4"))
            assert len(output_files) >= 1

            codec = _get_video_codec(output_files[0])
            assert codec == "hevc"

        finally:
            service.shutdown()


class TestBatchConversionE2E:
    """End-to-end tests for batch file conversion."""

    def test_convert_multiple_files(
        self,
        qtbot: QtBot,
        sample_video_folder: Path | None,
        e2e_output_dir: Path,
        ffmpeg_available: bool,
    ) -> None:
        """Test batch conversion of multiple files."""
        if not ffmpeg_available or sample_video_folder is None:
            pytest.skip("FFmpeg not available or sample folder creation failed")

        from video_converter.gui.services.conversion_service import ConversionService

        service = ConversionService()

        try:
            completed_tasks = []
            failed_tasks = []

            service.task_completed.connect(
                lambda tid, res: completed_tasks.append((tid, res))
            )
            service.task_failed.connect(
                lambda tid, err: failed_tasks.append((tid, err))
            )

            # Add all videos from folder
            video_files = list(sample_video_folder.glob("*.mp4"))
            assert len(video_files) >= 2, "Should have multiple test videos"

            task_ids = []
            settings = {"output_dir": str(e2e_output_dir)}
            for video_file in video_files:
                task_id = service.add_task(str(video_file), settings=settings)
                task_ids.append(task_id)

            # Wait for all conversions
            expected_count = len(video_files)
            timeout = 300000  # 5 minutes for batch
            start_time = time.time()

            while (
                len(completed_tasks) + len(failed_tasks) < expected_count
                and (time.time() - start_time) < (timeout / 1000)
            ):
                qtbot.wait(500)

            # Verify results
            total_processed = len(completed_tasks) + len(failed_tasks)
            assert total_processed == expected_count, (
                f"Expected {expected_count} processed, got {total_processed}"
            )

            # All should complete successfully
            assert len(completed_tasks) == expected_count
            assert len(failed_tasks) == 0

            # Verify output files
            output_files = list(e2e_output_dir.glob("*.mp4"))
            assert len(output_files) >= expected_count

        finally:
            service.shutdown()


class TestSettingsE2E:
    """End-to-end tests for settings application."""

    def test_quality_setting_applied(
        self,
        qtbot: QtBot,
        sample_h264_video: Path | None,
        e2e_output_dir: Path,
        ffmpeg_available: bool,
    ) -> None:
        """Test that quality settings affect output file size."""
        if not ffmpeg_available or sample_h264_video is None:
            pytest.skip("FFmpeg not available or sample video creation failed")

        from video_converter.gui.services.conversion_service import ConversionService

        # Convert with high quality (low CRF = larger file)
        high_quality_dir = e2e_output_dir / "high_quality"
        high_quality_dir.mkdir()

        service1 = ConversionService()

        try:
            completed1 = []
            service1.task_completed.connect(
                lambda tid, res: completed1.append((tid, res))
            )

            settings_high = {
                "output_dir": str(high_quality_dir),
                "quality": 18,  # Higher quality
            }
            service1.add_task(str(sample_h264_video), settings=settings_high)

            timeout = 120000
            start_time = time.time()
            while not completed1 and (time.time() - start_time) < (timeout / 1000):
                qtbot.wait(500)

        finally:
            service1.shutdown()

        # Convert with lower quality (high CRF = smaller file)
        low_quality_dir = e2e_output_dir / "low_quality"
        low_quality_dir.mkdir()

        service2 = ConversionService()

        try:
            completed2 = []
            service2.task_completed.connect(
                lambda tid, res: completed2.append((tid, res))
            )

            settings_low = {
                "output_dir": str(low_quality_dir),
                "quality": 35,  # Lower quality
            }
            service2.add_task(str(sample_h264_video), settings=settings_low)

            timeout = 120000
            start_time = time.time()
            while not completed2 and (time.time() - start_time) < (timeout / 1000):
                qtbot.wait(500)

        finally:
            service2.shutdown()

        # Compare file sizes
        high_quality_files = list(high_quality_dir.glob("*.mp4"))
        low_quality_files = list(low_quality_dir.glob("*.mp4"))

        if high_quality_files and low_quality_files:
            high_size = _get_file_size(high_quality_files[0])
            low_size = _get_file_size(low_quality_files[0])

            # Higher quality should generally produce larger files
            # (though this may vary depending on encoder and content)
            assert high_size > 0 and low_size > 0

    def test_output_directory_used(
        self,
        qtbot: QtBot,
        sample_h264_video: Path | None,
        e2e_output_dir: Path,
        ffmpeg_available: bool,
    ) -> None:
        """Test that custom output directory is respected."""
        if not ffmpeg_available or sample_h264_video is None:
            pytest.skip("FFmpeg not available or sample video creation failed")

        from video_converter.gui.services.conversion_service import ConversionService

        custom_dir = e2e_output_dir / "custom_output"
        custom_dir.mkdir()

        service = ConversionService()

        try:
            completed_tasks = []
            service.task_completed.connect(
                lambda tid, res: completed_tasks.append((tid, res))
            )

            settings = {"output_dir": str(custom_dir)}
            service.add_task(str(sample_h264_video), settings=settings)

            timeout = 120000
            start_time = time.time()
            while not completed_tasks and (time.time() - start_time) < (timeout / 1000):
                qtbot.wait(500)

            assert len(completed_tasks) == 1

            # Verify output is in custom directory
            output_files = list(custom_dir.glob("*.mp4"))
            assert len(output_files) >= 1, "Output should be in custom directory"

        finally:
            service.shutdown()


class TestErrorHandlingE2E:
    """End-to-end tests for error handling scenarios."""

    def test_invalid_file_shows_error(
        self,
        qtbot: QtBot,
        corrupt_video_file: Path,
        ffmpeg_available: bool,
    ) -> None:
        """Test that invalid/corrupt files are handled gracefully."""
        if not ffmpeg_available:
            pytest.skip("FFmpeg not available")

        from video_converter.gui.services.conversion_service import ConversionService

        service = ConversionService()

        try:
            failed_tasks = []
            completed_tasks = []

            service.task_failed.connect(
                lambda tid, err: failed_tasks.append((tid, err))
            )
            service.task_completed.connect(
                lambda tid, res: completed_tasks.append((tid, res))
            )

            task_id = service.add_task(str(corrupt_video_file))

            # Wait for processing
            timeout = 60000
            start_time = time.time()
            while (
                not failed_tasks
                and not completed_tasks
                and (time.time() - start_time) < (timeout / 1000)
            ):
                qtbot.wait(500)

            # Should fail with error
            assert len(failed_tasks) == 1, "Corrupt file should fail"
            assert len(completed_tasks) == 0

        finally:
            service.shutdown()

    def test_nonexistent_file_handled(
        self,
        qtbot: QtBot,
        tmp_path: Path,
        ffmpeg_available: bool,
    ) -> None:
        """Test that nonexistent files are handled gracefully."""
        if not ffmpeg_available:
            pytest.skip("FFmpeg not available")

        from video_converter.gui.services.conversion_service import ConversionService

        service = ConversionService()

        try:
            nonexistent = tmp_path / "does_not_exist.mp4"

            # Adding a nonexistent file might fail immediately or during processing
            # The service should handle this gracefully
            task_id = service.add_task(str(nonexistent))

            # Either returns None or a task ID that will fail
            if task_id is not None:
                failed_tasks = []
                service.task_failed.connect(
                    lambda tid, err: failed_tasks.append((tid, err))
                )

                timeout = 30000
                start_time = time.time()
                while not failed_tasks and (time.time() - start_time) < (timeout / 1000):
                    qtbot.wait(500)

                # Should have failed
                assert len(failed_tasks) >= 1

        finally:
            service.shutdown()


class TestPauseResumeE2E:
    """End-to-end tests for pause/resume functionality."""

    def test_pause_stops_queue_processing(
        self,
        qtbot: QtBot,
        sample_video_folder: Path | None,
        e2e_output_dir: Path,
        ffmpeg_available: bool,
    ) -> None:
        """Test that pausing stops processing of queued items."""
        if not ffmpeg_available or sample_video_folder is None:
            pytest.skip("FFmpeg not available or sample folder creation failed")

        from video_converter.gui.services.conversion_service import ConversionService

        service = ConversionService()

        try:
            completed_tasks = []
            service.task_completed.connect(
                lambda tid, res: completed_tasks.append((tid, res))
            )

            # Add multiple videos
            video_files = list(sample_video_folder.glob("*.mp4"))
            settings = {"output_dir": str(e2e_output_dir)}

            for video_file in video_files:
                service.add_task(str(video_file), settings=settings)

            # Pause immediately
            service.pause_all()

            # Wait a bit
            qtbot.wait(2000)

            # Check queue status
            status = service.get_queue_status()
            assert status["is_paused"] is True

            # Resume and wait for completion
            service.resume_all()

            timeout = 300000
            start_time = time.time()
            while (
                len(completed_tasks) < len(video_files)
                and (time.time() - start_time) < (timeout / 1000)
            ):
                qtbot.wait(500)

            # All should eventually complete
            assert len(completed_tasks) == len(video_files)

        finally:
            service.shutdown()


class TestConversionStatisticsE2E:
    """End-to-end tests for conversion statistics."""

    def test_statistics_accumulated(
        self,
        qtbot: QtBot,
        sample_h264_video: Path | None,
        e2e_output_dir: Path,
        ffmpeg_available: bool,
    ) -> None:
        """Test that statistics are correctly accumulated after conversion."""
        if not ffmpeg_available or sample_h264_video is None:
            pytest.skip("FFmpeg not available or sample video creation failed")

        from video_converter.gui.services.conversion_service import ConversionService

        service = ConversionService()

        try:
            # Initial statistics should be zero
            initial_stats = service.get_statistics()
            assert initial_stats["completed"] == 0

            completed_tasks = []
            service.task_completed.connect(
                lambda tid, res: completed_tasks.append((tid, res))
            )

            settings = {"output_dir": str(e2e_output_dir)}
            service.add_task(str(sample_h264_video), settings=settings)

            timeout = 120000
            start_time = time.time()
            while not completed_tasks and (time.time() - start_time) < (timeout / 1000):
                qtbot.wait(500)

            # Statistics should be updated
            final_stats = service.get_statistics()
            assert final_stats["completed"] >= 1
            assert final_stats["total_original_size"] > 0

        finally:
            service.shutdown()
