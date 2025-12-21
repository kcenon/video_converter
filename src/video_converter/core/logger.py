"""Logging system with file and console output.

This module provides a comprehensive logging system that outputs to both
file and console with configurable log levels, log rotation, and colored
console output using the Rich library.

SDS Reference: SDS-C01-002
SRS Reference: SRS-101 (Logging System)

Example:
    >>> from video_converter.core.logger import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("Starting conversion")
    >>> logger.debug("Processing file: %s", filename)
    >>> logger.error("Conversion failed", exc_info=True)

    >>> # Configure log level globally
    >>> from video_converter.core.logger import configure_logging
    >>> configure_logging(level="DEBUG", log_dir=Path("/custom/path"))
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Default configuration
DEFAULT_LOG_DIR = Path.home() / ".local" / "share" / "video_converter" / "logs"
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

# Custom theme for console output
CUSTOM_THEME = Theme(
    {
        "logging.level.debug": "dim cyan",
        "logging.level.info": "green",
        "logging.level.warning": "yellow",
        "logging.level.error": "bold red",
        "logging.level.critical": "bold white on red",
    }
)

# Global state
_log_dir: Path = DEFAULT_LOG_DIR
_log_level: int = DEFAULT_LOG_LEVEL
_initialized: bool = False
_console: Console | None = None


def _get_console() -> Console:
    """Get or create the Rich console instance.

    Returns:
        Console: The shared Rich console instance.
    """
    global _console
    if _console is None:
        _console = Console(theme=CUSTOM_THEME, stderr=True)
    return _console


def _ensure_log_dir() -> Path:
    """Ensure the log directory exists.

    Returns:
        Path: The log directory path.
    """
    _log_dir.mkdir(parents=True, exist_ok=True)
    return _log_dir


def _create_file_handler() -> RotatingFileHandler:
    """Create a rotating file handler for the logger.

    Returns:
        RotatingFileHandler: Configured file handler with rotation.
    """
    log_dir = _ensure_log_dir()
    log_file = log_dir / "video_converter.log"

    handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        fmt=DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
    )
    handler.setFormatter(formatter)
    handler.setLevel(_log_level)

    return handler


def _create_console_handler() -> RichHandler:
    """Create a Rich console handler with colored output.

    Returns:
        RichHandler: Configured Rich handler for console output.
    """
    handler = RichHandler(
        console=_get_console(),
        show_time=True,
        show_level=True,
        show_path=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        markup=True,
    )
    handler.setLevel(_log_level)

    return handler


def configure_logging(
    level: int | str = DEFAULT_LOG_LEVEL,
    log_dir: Path | None = None,
    console_output: bool = True,
    file_output: bool = True,
) -> None:
    """Configure the global logging settings.

    This function should be called once at application startup to configure
    the logging system. Subsequent calls will update the configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Can be either an integer or string.
        log_dir: Directory for log files. Default: ~/.local/share/video_converter/logs
        console_output: Whether to output logs to console. Default: True.
        file_output: Whether to output logs to file. Default: True.

    Example:
        >>> configure_logging(level="DEBUG")
        >>> configure_logging(level=logging.WARNING, log_dir=Path("/var/log/myapp"))
    """
    global _log_dir, _log_level, _initialized

    # Convert string level to int
    if isinstance(level, str):
        _log_level = getattr(logging, level.upper(), DEFAULT_LOG_LEVEL)
    else:
        _log_level = level

    if log_dir is not None:
        _log_dir = log_dir

    # Reset root logger configuration
    root_logger = logging.getLogger("video_converter")
    root_logger.setLevel(_log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    # Add handlers based on configuration
    if console_output:
        root_logger.addHandler(_create_console_handler())

    if file_output:
        root_logger.addHandler(_create_file_handler())

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    This is the primary function for obtaining a logger. It returns a logger
    that is a child of the "video_converter" root logger, ensuring consistent
    configuration across the application.

    Args:
        name: The name of the logger, typically __name__.

    Returns:
        Logger: Configured logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting conversion")
        >>> logger.debug("Processing file: %s", filename)
        >>> logger.error("Conversion failed", exc_info=True)
    """
    global _initialized

    # Ensure logging is configured on first use
    if not _initialized:
        configure_logging()

    # Create child logger under video_converter namespace
    logger_name = name if name.startswith("video_converter") else f"video_converter.{name}"
    logger = logging.getLogger(logger_name)

    return logger


def set_log_level(level: int | str) -> None:
    """Set the log level for all video_converter loggers.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Can be either an integer or string.

    Example:
        >>> set_log_level("DEBUG")
        >>> set_log_level(logging.WARNING)
    """
    global _log_level

    if isinstance(level, str):
        _log_level = getattr(logging, level.upper(), DEFAULT_LOG_LEVEL)
    else:
        _log_level = level

    # Update all handlers
    root_logger = logging.getLogger("video_converter")
    root_logger.setLevel(_log_level)

    for handler in root_logger.handlers:
        handler.setLevel(_log_level)


def get_log_file_path() -> Path:
    """Get the path to the current log file.

    Returns:
        Path: Path to the log file.
    """
    return _log_dir / "video_converter.log"


def get_log_dir() -> Path:
    """Get the log directory path.

    Returns:
        Path: Path to the log directory.
    """
    return _log_dir


class LogLevel:
    """Log level constants for convenient access.

    Attributes:
        DEBUG: Detailed information for debugging.
        INFO: General operational information.
        WARNING: Indication of potential issues.
        ERROR: Error that prevented an operation.
        CRITICAL: Critical error, application may not continue.
    """

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


__all__ = [
    "configure_logging",
    "get_logger",
    "get_log_dir",
    "get_log_file_path",
    "set_log_level",
    "LogLevel",
    "DEFAULT_LOG_DIR",
    "DEFAULT_LOG_LEVEL",
]
