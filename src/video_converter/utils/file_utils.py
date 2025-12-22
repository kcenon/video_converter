"""File utilities for path and size management.

This module provides utility functions for file operations including path
manipulation, size calculations, temporary file management, and disk space
checks.

SDS Reference: SDS-U01-002

Example:
    >>> from video_converter.utils.file_utils import (
    ...     expand_path,
    ...     format_size,
    ...     get_temp_path,
    ...     check_disk_space,
    ... )
    >>> path = expand_path("~/Videos/Converted")
    >>> print(path)
    /Users/username/Videos/Converted
    >>> print(format_size(1536000000))
    1.43 GB
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from typing import Generator

from video_converter.core.logger import get_logger

logger = get_logger(__name__)

# Constants
TEMP_DIR_PREFIX = "video_converter_"
SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]
BYTES_PER_UNIT = 1024

# Global set to track temporary files for cleanup
_temp_files: set[Path] = set()
_temp_dirs: set[Path] = set()


class InsufficientSpaceError(Exception):
    """Raised when there is not enough disk space for an operation.

    Attributes:
        path: The path where space was checked.
        required: Required space in bytes.
        available: Available space in bytes.
    """

    def __init__(self, path: Path, required: int, available: int) -> None:
        self.path = path
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient disk space at {path}: "
            f"required {format_size(required)}, available {format_size(available)}"
        )


class AtomicWriteError(Exception):
    """Raised when atomic write operation fails.

    Attributes:
        path: The target path for the write operation.
        reason: Description of why the write failed.
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Atomic write to {path} failed: {reason}")


def expand_path(path: str | Path) -> Path:
    """Expand user paths and resolve to absolute path.

    Expands ~ to user's home directory and resolves relative paths to
    absolute paths.

    Args:
        path: Path string or Path object to expand.

    Returns:
        Fully expanded and resolved absolute Path.

    Example:
        >>> expand_path("~/Videos/Converted")
        PosixPath('/Users/username/Videos/Converted')
        >>> expand_path("./relative/path")
        PosixPath('/current/working/dir/relative/path')
    """
    return Path(path).expanduser().resolve()


def format_size(size_bytes: int | float, precision: int = 2) -> str:
    """Format bytes into human-readable size string.

    Converts raw byte count to a human-readable format with appropriate
    unit suffix (B, KB, MB, GB, TB, PB).

    Args:
        size_bytes: Size in bytes.
        precision: Number of decimal places. Default is 2.

    Returns:
        Human-readable size string (e.g., "1.43 GB").

    Example:
        >>> format_size(1023)
        '1023 B'
        >>> format_size(1024)
        '1.00 KB'
        >>> format_size(1536000000)
        '1.43 GB'
    """
    if size_bytes < 0:
        return f"-{format_size(-size_bytes, precision)}"

    if size_bytes < BYTES_PER_UNIT:
        return f"{int(size_bytes)} B"

    size = float(size_bytes)
    for unit in SIZE_UNITS[1:]:
        size /= BYTES_PER_UNIT
        if size < BYTES_PER_UNIT:
            return f"{size:.{precision}f} {unit}"

    return f"{size:.{precision}f} {SIZE_UNITS[-1]}"


def parse_size(size_str: str) -> int:
    """Parse human-readable size string to bytes.

    Converts a human-readable size string back to bytes. Supports
    B, KB, MB, GB, TB, PB units (case-insensitive).

    Args:
        size_str: Size string to parse (e.g., "1.5 GB", "500MB").

    Returns:
        Size in bytes.

    Raises:
        ValueError: If the size string is invalid.

    Example:
        >>> parse_size("1.5 GB")
        1610612736
        >>> parse_size("500MB")
        524288000
    """
    size_str = size_str.strip().upper()

    # Handle plain bytes
    if size_str.isdigit():
        return int(size_str)

    # Find the numeric part and unit
    for i, char in enumerate(size_str):
        if char.isalpha():
            num_part = size_str[:i].strip()
            unit_part = size_str[i:].strip()
            break
    else:
        raise ValueError(f"Invalid size string: {size_str}")

    try:
        num = float(num_part)
    except ValueError:
        raise ValueError(f"Invalid numeric value in size string: {size_str}") from None

    # Normalize unit (remove trailing 'B' if present, handle 'K' -> 'KB')
    unit_part = unit_part.rstrip("B").strip()
    if not unit_part:
        unit_part = "B"
    elif len(unit_part) == 1 and unit_part != "B":
        unit_part = unit_part + "B"
    else:
        unit_part = unit_part + "B"

    try:
        unit_index = SIZE_UNITS.index(unit_part)
    except ValueError:
        raise ValueError(f"Unknown size unit: {unit_part}") from None

    return int(num * (BYTES_PER_UNIT**unit_index))


def get_temp_dir() -> Path:
    """Get the temporary directory for video converter operations.

    Creates a dedicated subdirectory in the system temp directory for
    video converter temporary files.

    Returns:
        Path to the temporary directory.
    """
    temp_base = Path(tempfile.gettempdir()) / "video_converter"
    temp_base.mkdir(parents=True, exist_ok=True)
    return temp_base


def get_temp_path(
    filename: str | Path,
    suffix: str | None = None,
    unique: bool = True,
) -> Path:
    """Generate a unique temporary file path.

    Creates a temporary file path in the video converter temp directory.
    The path is automatically registered for cleanup on exit.

    Args:
        filename: Original filename to base the temp name on.
        suffix: Optional suffix to append (e.g., ".mp4").
        unique: If True, adds a unique identifier to prevent conflicts.

    Returns:
        Path to the temporary file location.

    Example:
        >>> get_temp_path("vacation.mp4")
        PosixPath('/tmp/video_converter/vacation_a1b2c3d4.mp4')
        >>> get_temp_path("video", suffix=".hevc")
        PosixPath('/tmp/video_converter/video_e5f6g7h8.hevc')
    """
    temp_dir = get_temp_dir()
    original = Path(filename)

    if suffix is None:
        suffix = original.suffix

    stem = original.stem
    if unique:
        unique_id = uuid.uuid4().hex[:8]
        stem = f"{stem}_{unique_id}"

    temp_path = temp_dir / f"{stem}{suffix}"

    # Register for cleanup
    _temp_files.add(temp_path)

    logger.debug("Generated temp path: %s", temp_path)
    return temp_path


def create_temp_directory(prefix: str | None = None) -> Path:
    """Create a temporary directory for video converter operations.

    Creates a unique temporary directory that is automatically registered
    for cleanup on exit.

    Args:
        prefix: Optional prefix for the directory name.

    Returns:
        Path to the created temporary directory.

    Example:
        >>> temp_dir = create_temp_directory("conversion")
        >>> print(temp_dir)
        /tmp/video_converter/conversion_a1b2c3d4
    """
    temp_base = get_temp_dir()
    prefix = prefix or TEMP_DIR_PREFIX

    unique_id = uuid.uuid4().hex[:8]
    temp_dir = temp_base / f"{prefix}{unique_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Register for cleanup
    _temp_dirs.add(temp_dir)

    logger.debug("Created temp directory: %s", temp_dir)
    return temp_dir


def check_disk_space(path: str | Path) -> int:
    """Check available disk space at the given path.

    Args:
        path: Path to check disk space for.

    Returns:
        Available disk space in bytes.

    Example:
        >>> available = check_disk_space("/Users/username")
        >>> print(format_size(available))
        '128.5 GB'
    """
    path = expand_path(path)

    # Find an existing parent directory
    check_path = path
    while not check_path.exists():
        check_path = check_path.parent
        if check_path == check_path.parent:  # Reached root
            break

    usage = shutil.disk_usage(check_path)
    return usage.free


def ensure_disk_space(
    path: str | Path,
    required_bytes: int,
    multiplier: float = 2.0,
) -> None:
    """Ensure sufficient disk space is available.

    Checks if there is enough disk space at the given path. For video
    conversion, it's recommended to have at least 2x the input file size.

    Args:
        path: Path to check disk space for.
        required_bytes: Minimum required space in bytes.
        multiplier: Safety multiplier for required space. Default is 2.0.

    Raises:
        InsufficientSpaceError: If there is not enough disk space.

    Example:
        >>> ensure_disk_space("/output", input_size, multiplier=2.0)
    """
    path = expand_path(path)
    required = int(required_bytes * multiplier)
    available = check_disk_space(path)

    if available < required:
        raise InsufficientSpaceError(path, required, available)

    logger.debug(
        "Disk space check passed: required=%s, available=%s",
        format_size(required),
        format_size(available),
    )


def safe_move(src: str | Path, dst: str | Path, overwrite: bool = False) -> Path:
    """Safely move a file to a new location.

    Moves a file with proper error handling. If the destination already
    exists, behavior depends on the overwrite flag.

    Args:
        src: Source file path.
        dst: Destination file path.
        overwrite: If True, overwrite existing destination. Default is False.

    Returns:
        Path to the destination file.

    Raises:
        FileNotFoundError: If source file doesn't exist.
        FileExistsError: If destination exists and overwrite is False.
        OSError: If move operation fails.

    Example:
        >>> safe_move("/tmp/video.mp4", "/output/video.mp4")
        PosixPath('/output/video.mp4')
    """
    src_path = expand_path(src)
    dst_path = expand_path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f"Source file not found: {src_path}")

    if dst_path.exists() and not overwrite:
        raise FileExistsError(f"Destination already exists: {dst_path}")

    # Ensure destination directory exists
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove destination if overwriting
    if dst_path.exists() and overwrite:
        dst_path.unlink()

    shutil.move(str(src_path), str(dst_path))
    logger.debug("Moved file: %s -> %s", src_path, dst_path)

    return dst_path


def safe_copy(src: str | Path, dst: str | Path, overwrite: bool = False) -> Path:
    """Safely copy a file to a new location.

    Copies a file with proper error handling, preserving metadata.

    Args:
        src: Source file path.
        dst: Destination file path.
        overwrite: If True, overwrite existing destination. Default is False.

    Returns:
        Path to the destination file.

    Raises:
        FileNotFoundError: If source file doesn't exist.
        FileExistsError: If destination exists and overwrite is False.
        OSError: If copy operation fails.

    Example:
        >>> safe_copy("/input/video.mp4", "/backup/video.mp4")
        PosixPath('/backup/video.mp4')
    """
    src_path = expand_path(src)
    dst_path = expand_path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f"Source file not found: {src_path}")

    if dst_path.exists() and not overwrite:
        raise FileExistsError(f"Destination already exists: {dst_path}")

    # Ensure destination directory exists
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove destination if overwriting
    if dst_path.exists() and overwrite:
        dst_path.unlink()

    shutil.copy2(str(src_path), str(dst_path))
    logger.debug("Copied file: %s -> %s", src_path, dst_path)

    return dst_path


def safe_delete(path: str | Path, missing_ok: bool = True) -> bool:
    """Safely delete a file.

    Deletes a file with proper error handling.

    Args:
        path: Path to the file to delete.
        missing_ok: If True, don't raise error if file doesn't exist.

    Returns:
        True if file was deleted, False if it didn't exist.

    Raises:
        FileNotFoundError: If file doesn't exist and missing_ok is False.
        OSError: If deletion fails.

    Example:
        >>> safe_delete("/tmp/video.mp4")
        True
    """
    file_path = expand_path(path)

    if not file_path.exists():
        if missing_ok:
            return False
        raise FileNotFoundError(f"File not found: {file_path}")

    file_path.unlink()
    logger.debug("Deleted file: %s", file_path)

    return True


@contextmanager
def atomic_write(
    path: str | Path,
    mode: str = "wb",
) -> Generator[Path, None, None]:
    """Context manager for atomic file writes.

    Writes to a temporary file first, then atomically moves it to the
    target location. This prevents file corruption if the write is
    interrupted.

    Args:
        path: Target file path.
        mode: File open mode. Default is "wb" (write binary).

    Yields:
        Path to the temporary file to write to.

    Raises:
        AtomicWriteError: If the atomic move fails.

    Example:
        >>> with atomic_write("/output/video.mp4") as temp_path:
        ...     # Write to temp_path
        ...     shutil.copy("input.mp4", temp_path)
        >>> # File is now atomically moved to /output/video.mp4
    """
    target_path = expand_path(path)
    temp_path = get_temp_path(target_path.name)

    try:
        yield temp_path

        # If we get here, write was successful - move to target
        if temp_path.exists():
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Atomic move
            shutil.move(str(temp_path), str(target_path))
            logger.debug("Atomic write completed: %s", target_path)

    except Exception as e:
        # Clean up temp file on failure
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise AtomicWriteError(target_path, str(e)) from e

    finally:
        # Remove from tracking since we handled it
        _temp_files.discard(temp_path)


def get_file_size(path: str | Path) -> int:
    """Get the size of a file in bytes.

    Args:
        path: Path to the file.

    Returns:
        File size in bytes.

    Raises:
        FileNotFoundError: If file doesn't exist.

    Example:
        >>> size = get_file_size("/path/to/video.mp4")
        >>> print(format_size(size))
        '1.5 GB'
    """
    file_path = expand_path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return file_path.stat().st_size


def get_directory_size(path: str | Path) -> int:
    """Get the total size of all files in a directory.

    Recursively calculates the total size of all files in a directory.

    Args:
        path: Path to the directory.

    Returns:
        Total size in bytes.

    Raises:
        NotADirectoryError: If path is not a directory.

    Example:
        >>> size = get_directory_size("/path/to/videos")
        >>> print(format_size(size))
        '15.3 GB'
    """
    dir_path = expand_path(path)

    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    total_size = 0
    for file_path in dir_path.rglob("*"):
        if file_path.is_file():
            total_size += file_path.stat().st_size

    return total_size


def cleanup_temp_files() -> int:
    """Clean up all registered temporary files and directories.

    Removes all temporary files and directories that were created using
    get_temp_path() and create_temp_directory().

    Returns:
        Number of items cleaned up.
    """
    cleaned = 0

    # Clean up files
    for temp_file in list(_temp_files):
        try:
            if temp_file.exists():
                temp_file.unlink()
                cleaned += 1
                logger.debug("Cleaned up temp file: %s", temp_file)
        except OSError as e:
            logger.warning("Failed to clean up temp file %s: %s", temp_file, e)
        finally:
            _temp_files.discard(temp_file)

    # Clean up directories
    for temp_dir in list(_temp_dirs):
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                cleaned += 1
                logger.debug("Cleaned up temp directory: %s", temp_dir)
        except OSError as e:
            logger.warning("Failed to clean up temp directory %s: %s", temp_dir, e)
        finally:
            _temp_dirs.discard(temp_dir)

    if cleaned > 0:
        logger.info("Cleaned up %d temporary items", cleaned)

    return cleaned


def ensure_directory(path: str | Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory.

    Returns:
        Path to the directory.

    Example:
        >>> ensure_directory("~/Videos/Converted")
        PosixPath('/Users/username/Videos/Converted')
    """
    dir_path = expand_path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def is_video_file(path: str | Path) -> bool:
    """Check if a path points to a video file based on extension.

    Args:
        path: Path to check.

    Returns:
        True if the file has a video extension.

    Example:
        >>> is_video_file("/path/to/video.mp4")
        True
        >>> is_video_file("/path/to/image.jpg")
        False
    """
    video_extensions = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".wmv", ".webm"}
    file_path = Path(path)
    return file_path.suffix.lower() in video_extensions


def generate_output_path(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    suffix: str = "_hevc",
    extension: str | None = None,
) -> Path:
    """Generate an output path for a converted video.

    Args:
        input_path: Path to the input video.
        output_dir: Directory for output. If None, uses input directory.
        suffix: Suffix to add to filename. Default is "_hevc".
        extension: New file extension. If None, keeps original.

    Returns:
        Generated output path.

    Example:
        >>> generate_output_path("/input/video.mp4")
        PosixPath('/input/video_hevc.mp4')
        >>> generate_output_path("/input/video.mp4", "/output", suffix="")
        PosixPath('/output/video.mp4')
    """
    input_path = expand_path(input_path)

    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = expand_path(output_dir)

    stem = input_path.stem
    ext = extension if extension else input_path.suffix

    if not ext.startswith("."):
        ext = f".{ext}"

    return output_dir / f"{stem}{suffix}{ext}"


# Register cleanup on exit
atexit.register(cleanup_temp_files)


__all__ = [
    # Exceptions
    "InsufficientSpaceError",
    "AtomicWriteError",
    # Path utilities
    "expand_path",
    "ensure_directory",
    "generate_output_path",
    # Size utilities
    "format_size",
    "parse_size",
    "get_file_size",
    "get_directory_size",
    # Temp file utilities
    "get_temp_dir",
    "get_temp_path",
    "create_temp_directory",
    "cleanup_temp_files",
    # Disk space utilities
    "check_disk_space",
    "ensure_disk_space",
    # File operations
    "safe_move",
    "safe_copy",
    "safe_delete",
    "atomic_write",
    # File checks
    "is_video_file",
]
