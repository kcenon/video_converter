"""Unit tests for logging system module."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from video_converter.core.logger import (
    DEFAULT_LOG_DIR,
    DEFAULT_LOG_LEVEL,
    LogLevel,
    configure_logging,
    get_log_dir,
    get_log_file_path,
    get_logger,
    set_log_level,
)


class TestLogLevel:
    """Tests for LogLevel constants."""

    def test_debug_level(self) -> None:
        """Test DEBUG level value."""
        assert LogLevel.DEBUG == logging.DEBUG

    def test_info_level(self) -> None:
        """Test INFO level value."""
        assert LogLevel.INFO == logging.INFO

    def test_warning_level(self) -> None:
        """Test WARNING level value."""
        assert LogLevel.WARNING == logging.WARNING

    def test_error_level(self) -> None:
        """Test ERROR level value."""
        assert LogLevel.ERROR == logging.ERROR

    def test_critical_level(self) -> None:
        """Test CRITICAL level value."""
        assert LogLevel.CRITICAL == logging.CRITICAL


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_logger(self) -> None:
        """Test that get_logger returns a Logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_dunder_name(self) -> None:
        """Test get_logger with __name__ style argument."""
        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)
        assert "video_converter" in logger.name

    def test_get_logger_adds_prefix(self) -> None:
        """Test that get_logger adds video_converter prefix."""
        logger = get_logger("my_module")
        assert logger.name == "video_converter.my_module"

    def test_get_logger_keeps_existing_prefix(self) -> None:
        """Test that get_logger keeps existing prefix."""
        logger = get_logger("video_converter.core.test")
        assert logger.name == "video_converter.core.test"

    def test_logger_can_log_info(self) -> None:
        """Test that logger can log info messages."""
        logger = get_logger("test_info")
        # Should not raise
        logger.info("Test message")

    def test_logger_can_log_debug(self) -> None:
        """Test that logger can log debug messages."""
        logger = get_logger("test_debug")
        # Should not raise
        logger.debug("Debug message: %s", "test")

    def test_logger_can_log_error(self) -> None:
        """Test that logger can log error messages."""
        logger = get_logger("test_error")
        # Should not raise
        logger.error("Error message")

    def test_logger_can_log_with_exception(self) -> None:
        """Test that logger can log with exception info."""
        logger = get_logger("test_exception")
        try:
            raise ValueError("Test error")
        except ValueError:
            # Should not raise
            logger.error("Caught exception", exc_info=True)


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_with_string_level(self) -> None:
        """Test configuring with string log level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                level="DEBUG",
                log_dir=Path(tmpdir),
                console_output=False,
                file_output=True,
            )
            logger = logging.getLogger("video_converter")
            assert logger.level == logging.DEBUG

    def test_configure_with_int_level(self) -> None:
        """Test configuring with integer log level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                level=logging.WARNING,
                log_dir=Path(tmpdir),
                console_output=False,
                file_output=True,
            )
            logger = logging.getLogger("video_converter")
            assert logger.level == logging.WARNING

    def test_configure_creates_log_dir(self) -> None:
        """Test that configure_logging creates log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs" / "nested"
            configure_logging(
                log_dir=log_dir,
                console_output=False,
                file_output=True,
            )
            assert log_dir.exists()

    def test_configure_with_console_only(self) -> None:
        """Test configuring with console output only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_dir=Path(tmpdir),
                console_output=True,
                file_output=False,
            )
            logger = logging.getLogger("video_converter")
            # Should have at least one handler (console)
            assert len(logger.handlers) >= 1

    def test_configure_with_file_only(self) -> None:
        """Test configuring with file output only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_dir=Path(tmpdir),
                console_output=False,
                file_output=True,
            )
            logger = logging.getLogger("video_converter")
            # Should have exactly one handler (file)
            assert len(logger.handlers) == 1

    def test_configure_multiple_times(self) -> None:
        """Test that configure_logging can be called multiple times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                level="DEBUG",
                log_dir=Path(tmpdir),
                console_output=False,
                file_output=True,
            )
            configure_logging(
                level="WARNING",
                log_dir=Path(tmpdir),
                console_output=False,
                file_output=True,
            )
            logger = logging.getLogger("video_converter")
            assert logger.level == logging.WARNING


class TestSetLogLevel:
    """Tests for set_log_level function."""

    def test_set_level_with_string(self) -> None:
        """Test setting log level with string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_dir=Path(tmpdir),
                console_output=False,
                file_output=True,
            )
            set_log_level("DEBUG")
            logger = logging.getLogger("video_converter")
            assert logger.level == logging.DEBUG

    def test_set_level_with_int(self) -> None:
        """Test setting log level with integer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_dir=Path(tmpdir),
                console_output=False,
                file_output=True,
            )
            set_log_level(logging.ERROR)
            logger = logging.getLogger("video_converter")
            assert logger.level == logging.ERROR

    def test_set_level_updates_handlers(self) -> None:
        """Test that set_log_level updates handler levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_dir=Path(tmpdir),
                console_output=False,
                file_output=True,
            )
            set_log_level(logging.CRITICAL)
            logger = logging.getLogger("video_converter")
            for handler in logger.handlers:
                assert handler.level == logging.CRITICAL


class TestLogFilePath:
    """Tests for log file path functions."""

    def test_get_log_file_path(self) -> None:
        """Test getting log file path."""
        path = get_log_file_path()
        assert isinstance(path, Path)
        assert path.name == "video_converter.log"

    def test_get_log_dir(self) -> None:
        """Test getting log directory."""
        log_dir = get_log_dir()
        assert isinstance(log_dir, Path)

    def test_default_log_dir(self) -> None:
        """Test default log directory value."""
        assert Path.home() / ".local" / "share" / "video_converter" / "logs" == DEFAULT_LOG_DIR

    def test_default_log_level(self) -> None:
        """Test default log level value."""
        assert DEFAULT_LOG_LEVEL == logging.INFO


class TestLogOutput:
    """Tests for log output functionality."""

    def test_file_logging(self) -> None:
        """Test that logs are written to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            configure_logging(
                log_dir=log_dir,
                console_output=False,
                file_output=True,
            )

            logger = get_logger("test_file_output")
            test_message = "Test file logging message"
            logger.info(test_message)

            # Force flush by closing handlers
            root_logger = logging.getLogger("video_converter")
            for handler in root_logger.handlers:
                handler.flush()

            log_file = log_dir / "video_converter.log"
            assert log_file.exists()

            content = log_file.read_text()
            assert test_message in content

    def test_log_format(self) -> None:
        """Test that log format includes expected components."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            configure_logging(
                log_dir=log_dir,
                console_output=False,
                file_output=True,
            )

            logger = get_logger("test_format")
            logger.info("Format test message")

            root_logger = logging.getLogger("video_converter")
            for handler in root_logger.handlers:
                handler.flush()

            log_file = log_dir / "video_converter.log"
            content = log_file.read_text()

            # Check format components
            assert "INFO" in content
            assert "test_format" in content
            assert "Format test message" in content


class TestLogRotation:
    """Tests for log rotation functionality."""

    def test_rotating_handler_configured(self) -> None:
        """Test that rotating file handler is configured correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                log_dir=Path(tmpdir),
                console_output=False,
                file_output=True,
            )

            from logging.handlers import RotatingFileHandler

            root_logger = logging.getLogger("video_converter")
            file_handlers = [h for h in root_logger.handlers if isinstance(h, RotatingFileHandler)]
            assert len(file_handlers) == 1

            handler = file_handlers[0]
            assert handler.maxBytes == 10 * 1024 * 1024  # 10 MB
            assert handler.backupCount == 5
