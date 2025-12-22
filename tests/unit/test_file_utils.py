"""Unit tests for file_utils module."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from video_converter.utils.file_utils import (
    AtomicWriteError,
    InsufficientSpaceError,
    atomic_write,
    check_disk_space,
    cleanup_temp_files,
    create_temp_directory,
    ensure_directory,
    ensure_disk_space,
    expand_path,
    format_size,
    generate_output_path,
    get_directory_size,
    get_file_size,
    get_temp_dir,
    get_temp_path,
    is_video_file,
    parse_size,
    safe_copy,
    safe_delete,
    safe_move,
)


class TestExpandPath:
    """Tests for expand_path function."""

    def test_expand_home_directory(self) -> None:
        """Test that ~ is expanded to home directory."""
        result = expand_path("~/Videos")
        assert str(result).startswith(str(Path.home()))
        assert result.is_absolute()

    def test_resolve_relative_path(self) -> None:
        """Test that relative paths are resolved to absolute."""
        result = expand_path("./relative/path")
        assert result.is_absolute()

    def test_path_object_input(self) -> None:
        """Test that Path objects are handled correctly."""
        result = expand_path(Path("~/test"))
        assert result.is_absolute()

    def test_already_absolute_path(self) -> None:
        """Test that absolute paths remain unchanged."""
        result = expand_path("/absolute/path")
        assert str(result) == "/absolute/path"


class TestFormatSize:
    """Tests for format_size function."""

    def test_bytes(self) -> None:
        """Test formatting bytes."""
        assert format_size(0) == "0 B"
        assert format_size(1) == "1 B"
        assert format_size(1023) == "1023 B"

    def test_kilobytes(self) -> None:
        """Test formatting kilobytes."""
        assert format_size(1024) == "1.00 KB"
        assert format_size(1536) == "1.50 KB"

    def test_megabytes(self) -> None:
        """Test formatting megabytes."""
        assert format_size(1024 * 1024) == "1.00 MB"
        assert format_size(1536 * 1024) == "1.50 MB"

    def test_gigabytes(self) -> None:
        """Test formatting gigabytes."""
        assert format_size(1024 * 1024 * 1024) == "1.00 GB"
        assert format_size(1536000000) == "1.43 GB"

    def test_terabytes(self) -> None:
        """Test formatting terabytes."""
        assert format_size(1024**4) == "1.00 TB"

    def test_negative_size(self) -> None:
        """Test formatting negative sizes."""
        assert format_size(-1024) == "-1.00 KB"

    def test_custom_precision(self) -> None:
        """Test custom precision."""
        assert format_size(1536000000, precision=1) == "1.4 GB"
        assert format_size(1536000000, precision=3) == "1.431 GB"


class TestParseSize:
    """Tests for parse_size function."""

    def test_parse_bytes(self) -> None:
        """Test parsing bytes."""
        assert parse_size("1023") == 1023
        assert parse_size("1023 B") == 1023
        assert parse_size("1023B") == 1023

    def test_parse_kilobytes(self) -> None:
        """Test parsing kilobytes."""
        assert parse_size("1 KB") == 1024
        assert parse_size("1KB") == 1024
        assert parse_size("1.5 KB") == 1536
        assert parse_size("1 K") == 1024

    def test_parse_megabytes(self) -> None:
        """Test parsing megabytes."""
        assert parse_size("1 MB") == 1024 * 1024
        assert parse_size("1MB") == 1024 * 1024

    def test_parse_gigabytes(self) -> None:
        """Test parsing gigabytes."""
        assert parse_size("1 GB") == 1024**3
        assert parse_size("1.5 GB") == int(1.5 * 1024**3)

    def test_case_insensitive(self) -> None:
        """Test case insensitivity."""
        assert parse_size("1 kb") == 1024
        assert parse_size("1 Kb") == 1024
        assert parse_size("1 gb") == 1024**3

    def test_invalid_size_string(self) -> None:
        """Test that invalid size strings raise ValueError."""
        with pytest.raises(ValueError):
            parse_size("invalid")

        with pytest.raises(ValueError):
            parse_size("1 XB")


class TestGetTempDir:
    """Tests for get_temp_dir function."""

    def test_returns_path_in_system_temp(self) -> None:
        """Test that temp dir is in system temp directory."""
        result = get_temp_dir()
        assert tempfile.gettempdir() in str(result)
        assert "video_converter" in str(result)

    def test_creates_directory(self) -> None:
        """Test that the directory is created."""
        result = get_temp_dir()
        assert result.exists()
        assert result.is_dir()


class TestGetTempPath:
    """Tests for get_temp_path function."""

    def test_generates_unique_path(self) -> None:
        """Test that unique paths are generated."""
        path1 = get_temp_path("test.mp4")
        path2 = get_temp_path("test.mp4")
        assert path1 != path2

    def test_preserves_extension(self) -> None:
        """Test that file extension is preserved."""
        result = get_temp_path("video.mp4")
        assert result.suffix == ".mp4"

    def test_custom_suffix(self) -> None:
        """Test custom suffix override."""
        result = get_temp_path("video.mp4", suffix=".hevc")
        assert result.suffix == ".hevc"

    def test_non_unique_path(self) -> None:
        """Test non-unique path generation."""
        path1 = get_temp_path("test.mp4", unique=False)
        path2 = get_temp_path("test.mp4", unique=False)
        assert path1 == path2


class TestCreateTempDirectory:
    """Tests for create_temp_directory function."""

    def test_creates_directory(self) -> None:
        """Test that directory is created."""
        result = create_temp_directory()
        assert result.exists()
        assert result.is_dir()

    def test_custom_prefix(self) -> None:
        """Test custom prefix."""
        result = create_temp_directory(prefix="myprefix_")
        assert "myprefix_" in result.name


class TestCheckDiskSpace:
    """Tests for check_disk_space function."""

    def test_returns_positive_value(self) -> None:
        """Test that disk space is a positive value."""
        result = check_disk_space("/")
        assert result > 0

    def test_works_with_home_directory(self) -> None:
        """Test with home directory."""
        result = check_disk_space("~")
        assert result > 0

    def test_works_with_nonexistent_path(self) -> None:
        """Test with non-existent path (checks parent)."""
        result = check_disk_space("/nonexistent/path/that/does/not/exist")
        assert result > 0


class TestEnsureDiskSpace:
    """Tests for ensure_disk_space function."""

    def test_passes_when_enough_space(self) -> None:
        """Test that no exception is raised when there's enough space."""
        # Request a very small amount of space
        ensure_disk_space("/", 1024)  # 1 KB

    def test_raises_when_not_enough_space(self) -> None:
        """Test that InsufficientSpaceError is raised when not enough space."""
        # Request an impossibly large amount of space
        with pytest.raises(InsufficientSpaceError) as exc_info:
            ensure_disk_space("/", 10**18)  # 1 EB
        assert "Insufficient disk space" in str(exc_info.value)


class TestSafeMove:
    """Tests for safe_move function."""

    def test_move_file(self, tmp_path: Path) -> None:
        """Test moving a file."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("content")

        result = safe_move(src, dst)
        assert result == dst
        assert dst.exists()
        assert not src.exists()

    def test_move_creates_parent_dir(self, tmp_path: Path) -> None:
        """Test that parent directories are created."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "subdir" / "dest.txt"
        src.write_text("content")

        result = safe_move(src, dst)
        assert dst.exists()

    def test_move_raises_when_source_missing(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised when source is missing."""
        src = tmp_path / "nonexistent.txt"
        dst = tmp_path / "dest.txt"

        with pytest.raises(FileNotFoundError):
            safe_move(src, dst)

    def test_move_raises_when_dest_exists(self, tmp_path: Path) -> None:
        """Test that FileExistsError is raised when dest exists."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("source")
        dst.write_text("dest")

        with pytest.raises(FileExistsError):
            safe_move(src, dst)

    def test_move_overwrites_when_flag_set(self, tmp_path: Path) -> None:
        """Test that overwrite flag works."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("new content")
        dst.write_text("old content")

        safe_move(src, dst, overwrite=True)
        assert dst.read_text() == "new content"


class TestSafeCopy:
    """Tests for safe_copy function."""

    def test_copy_file(self, tmp_path: Path) -> None:
        """Test copying a file."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("content")

        result = safe_copy(src, dst)
        assert result == dst
        assert dst.exists()
        assert src.exists()  # Source should still exist

    def test_copy_preserves_content(self, tmp_path: Path) -> None:
        """Test that content is preserved."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("test content")

        safe_copy(src, dst)
        assert dst.read_text() == "test content"

    def test_copy_raises_when_dest_exists(self, tmp_path: Path) -> None:
        """Test that FileExistsError is raised when dest exists."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("source")
        dst.write_text("dest")

        with pytest.raises(FileExistsError):
            safe_copy(src, dst)


class TestSafeDelete:
    """Tests for safe_delete function."""

    def test_delete_file(self, tmp_path: Path) -> None:
        """Test deleting a file."""
        file = tmp_path / "test.txt"
        file.write_text("content")

        result = safe_delete(file)
        assert result is True
        assert not file.exists()

    def test_delete_missing_file_ok(self, tmp_path: Path) -> None:
        """Test that missing_ok=True doesn't raise."""
        file = tmp_path / "nonexistent.txt"

        result = safe_delete(file, missing_ok=True)
        assert result is False

    def test_delete_missing_file_raises(self, tmp_path: Path) -> None:
        """Test that missing_ok=False raises."""
        file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            safe_delete(file, missing_ok=False)


class TestAtomicWrite:
    """Tests for atomic_write context manager."""

    def test_successful_write(self, tmp_path: Path) -> None:
        """Test successful atomic write."""
        target = tmp_path / "output.txt"

        with atomic_write(target) as temp_path:
            temp_path.write_text("content")

        assert target.exists()
        assert target.read_text() == "content"

    def test_failed_write_cleans_up(self, tmp_path: Path) -> None:
        """Test that temp file is cleaned up on failure."""
        target = tmp_path / "output.txt"

        with pytest.raises(AtomicWriteError):
            with atomic_write(target) as temp_path:
                temp_path.write_text("content")
                raise ValueError("Simulated failure")

        assert not target.exists()


class TestGetFileSize:
    """Tests for get_file_size function."""

    def test_get_size(self, tmp_path: Path) -> None:
        """Test getting file size."""
        file = tmp_path / "test.txt"
        file.write_text("hello")  # 5 bytes

        result = get_file_size(file)
        assert result == 5

    def test_raises_for_nonexistent(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            get_file_size(tmp_path / "nonexistent.txt")


class TestGetDirectorySize:
    """Tests for get_directory_size function."""

    def test_get_size(self, tmp_path: Path) -> None:
        """Test getting directory size."""
        (tmp_path / "file1.txt").write_text("hello")  # 5 bytes
        (tmp_path / "file2.txt").write_text("world")  # 5 bytes

        result = get_directory_size(tmp_path)
        assert result == 10

    def test_recursive_size(self, tmp_path: Path) -> None:
        """Test that subdirectories are included."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "file1.txt").write_text("hello")  # 5 bytes
        (subdir / "file2.txt").write_text("world")  # 5 bytes

        result = get_directory_size(tmp_path)
        assert result == 10

    def test_raises_for_file(self, tmp_path: Path) -> None:
        """Test that NotADirectoryError is raised for files."""
        file = tmp_path / "test.txt"
        file.write_text("content")

        with pytest.raises(NotADirectoryError):
            get_directory_size(file)


class TestCleanupTempFiles:
    """Tests for cleanup_temp_files function."""

    def test_cleans_up_temp_files(self) -> None:
        """Test that temp files are cleaned up."""
        temp_path = get_temp_path("test.txt")
        temp_path.write_text("content")

        count = cleanup_temp_files()
        assert count >= 1
        assert not temp_path.exists()

    def test_cleans_up_temp_directories(self) -> None:
        """Test that temp directories are cleaned up."""
        temp_dir = create_temp_directory()
        assert temp_dir.exists()

        count = cleanup_temp_files()
        assert count >= 1
        assert not temp_dir.exists()


class TestEnsureDirectory:
    """Tests for ensure_directory function."""

    def test_creates_directory(self, tmp_path: Path) -> None:
        """Test that directory is created."""
        new_dir = tmp_path / "new" / "nested" / "dir"

        result = ensure_directory(new_dir)
        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_existing_directory_ok(self, tmp_path: Path) -> None:
        """Test that existing directory doesn't raise."""
        result = ensure_directory(tmp_path)
        assert result == tmp_path


class TestIsVideoFile:
    """Tests for is_video_file function."""

    def test_video_extensions(self) -> None:
        """Test that video extensions are recognized."""
        assert is_video_file("video.mp4") is True
        assert is_video_file("video.mov") is True
        assert is_video_file("video.m4v") is True
        assert is_video_file("video.mkv") is True
        assert is_video_file("video.avi") is True
        assert is_video_file("video.webm") is True

    def test_non_video_extensions(self) -> None:
        """Test that non-video extensions are rejected."""
        assert is_video_file("image.jpg") is False
        assert is_video_file("document.pdf") is False
        assert is_video_file("audio.mp3") is False

    def test_case_insensitive(self) -> None:
        """Test case insensitivity."""
        assert is_video_file("video.MP4") is True
        assert is_video_file("video.MOV") is True


class TestGenerateOutputPath:
    """Tests for generate_output_path function."""

    def test_default_suffix(self, tmp_path: Path) -> None:
        """Test default _hevc suffix."""
        input_path = tmp_path / "video.mp4"
        input_path.write_text("dummy")

        result = generate_output_path(input_path)
        assert result.name == "video_hevc.mp4"
        assert result.parent == tmp_path

    def test_custom_output_dir(self, tmp_path: Path) -> None:
        """Test custom output directory."""
        input_path = tmp_path / "input" / "video.mp4"
        output_dir = tmp_path / "output"

        result = generate_output_path(input_path, output_dir=output_dir)
        assert result.parent == output_dir
        assert result.name == "video_hevc.mp4"

    def test_custom_suffix(self, tmp_path: Path) -> None:
        """Test custom suffix."""
        input_path = tmp_path / "video.mp4"

        result = generate_output_path(input_path, suffix="_converted")
        assert result.name == "video_converted.mp4"

    def test_empty_suffix(self, tmp_path: Path) -> None:
        """Test empty suffix."""
        input_path = tmp_path / "video.mp4"

        result = generate_output_path(input_path, suffix="")
        assert result.name == "video.mp4"

    def test_custom_extension(self, tmp_path: Path) -> None:
        """Test custom extension."""
        input_path = tmp_path / "video.mp4"

        result = generate_output_path(input_path, extension=".mkv")
        assert result.suffix == ".mkv"


class TestInsufficientSpaceError:
    """Tests for InsufficientSpaceError exception."""

    def test_error_message(self) -> None:
        """Test error message format."""
        error = InsufficientSpaceError(
            path=Path("/output"),
            required=1024 * 1024 * 1024,  # 1 GB
            available=512 * 1024 * 1024,  # 512 MB
        )
        assert "Insufficient disk space" in str(error)
        assert "/output" in str(error)
        assert "1.00 GB" in str(error)
        assert "512.00 MB" in str(error)

    def test_attributes(self) -> None:
        """Test exception attributes."""
        error = InsufficientSpaceError(
            path=Path("/output"),
            required=1000,
            available=500,
        )
        assert error.path == Path("/output")
        assert error.required == 1000
        assert error.available == 500


class TestAtomicWriteError:
    """Tests for AtomicWriteError exception."""

    def test_error_message(self) -> None:
        """Test error message format."""
        error = AtomicWriteError(path=Path("/output/file.mp4"), reason="disk full")
        assert "Atomic write" in str(error)
        assert "/output/file.mp4" in str(error)
        assert "disk full" in str(error)

    def test_attributes(self) -> None:
        """Test exception attributes."""
        error = AtomicWriteError(path=Path("/output/file.mp4"), reason="disk full")
        assert error.path == Path("/output/file.mp4")
        assert error.reason == "disk full"
