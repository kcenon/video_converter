"""Unit tests for launchd plist generator."""

from __future__ import annotations

import plistlib
import tempfile
from pathlib import Path

import pytest

from video_converter.automation.launchd import (
    DEFAULT_LAUNCH_AGENTS_DIR,
    DEFAULT_LOG_DIR,
    DEFAULT_PLIST_NAME,
    SERVICE_LABEL,
    LaunchdConfig,
    LaunchdPlistGenerator,
    LaunchdSchedule,
    generate_daily_plist,
    generate_watch_plist,
    validate_plist_syntax,
)


class TestLaunchdSchedule:
    """Tests for LaunchdSchedule dataclass."""

    def test_default_values(self) -> None:
        """Test default schedule values."""
        schedule = LaunchdSchedule()
        assert schedule.hour is None
        assert schedule.minute == 0
        assert schedule.weekday is None

    def test_daily_schedule(self) -> None:
        """Test daily schedule at 3 AM."""
        schedule = LaunchdSchedule(hour=3, minute=0)
        assert schedule.hour == 3
        assert schedule.minute == 0
        assert schedule.weekday is None

    def test_weekly_schedule(self) -> None:
        """Test weekly schedule on Monday at 9 AM."""
        schedule = LaunchdSchedule(hour=9, minute=30, weekday=1)
        assert schedule.hour == 9
        assert schedule.minute == 30
        assert schedule.weekday == 1

    def test_to_calendar_interval_daily(self) -> None:
        """Test conversion to calendar interval for daily schedule."""
        schedule = LaunchdSchedule(hour=3, minute=15)
        interval = schedule.to_calendar_interval()
        assert interval == {"Hour": 3, "Minute": 15}

    def test_to_calendar_interval_weekly(self) -> None:
        """Test conversion to calendar interval for weekly schedule."""
        schedule = LaunchdSchedule(hour=9, minute=0, weekday=0)
        interval = schedule.to_calendar_interval()
        assert interval == {"Hour": 9, "Minute": 0, "Weekday": 0}

    def test_to_calendar_interval_minute_only(self) -> None:
        """Test conversion to calendar interval with minute only."""
        schedule = LaunchdSchedule(minute=30)
        interval = schedule.to_calendar_interval()
        assert interval == {"Minute": 30}

    def test_invalid_hour_negative(self) -> None:
        """Test validation rejects negative hour."""
        with pytest.raises(ValueError, match="Hour must be 0-23"):
            LaunchdSchedule(hour=-1)

    def test_invalid_hour_high(self) -> None:
        """Test validation rejects hour > 23."""
        with pytest.raises(ValueError, match="Hour must be 0-23"):
            LaunchdSchedule(hour=24)

    def test_invalid_minute_negative(self) -> None:
        """Test validation rejects negative minute."""
        with pytest.raises(ValueError, match="Minute must be 0-59"):
            LaunchdSchedule(minute=-1)

    def test_invalid_minute_high(self) -> None:
        """Test validation rejects minute > 59."""
        with pytest.raises(ValueError, match="Minute must be 0-59"):
            LaunchdSchedule(minute=60)

    def test_invalid_weekday_negative(self) -> None:
        """Test validation rejects negative weekday."""
        with pytest.raises(ValueError, match="Weekday must be 0-6"):
            LaunchdSchedule(weekday=-1)

    def test_invalid_weekday_high(self) -> None:
        """Test validation rejects weekday > 6."""
        with pytest.raises(ValueError, match="Weekday must be 0-6"):
            LaunchdSchedule(weekday=7)


class TestLaunchdConfig:
    """Tests for LaunchdConfig dataclass."""

    def test_with_schedule(self) -> None:
        """Test config with schedule."""
        schedule = LaunchdSchedule(hour=3, minute=0)
        config = LaunchdConfig(
            program_args=["python", "-m", "video_converter"],
            schedule=schedule,
        )
        assert config.label == SERVICE_LABEL
        assert config.schedule == schedule
        assert config.watch_paths == []

    def test_with_watch_paths(self) -> None:
        """Test config with watch paths."""
        config = LaunchdConfig(
            program_args=["python", "-m", "video_converter"],
            watch_paths=[Path("/tmp/watch")],
        )
        assert config.schedule is None
        assert len(config.watch_paths) == 1

    def test_with_both(self) -> None:
        """Test config with both schedule and watch paths."""
        schedule = LaunchdSchedule(hour=3, minute=0)
        config = LaunchdConfig(
            program_args=["python", "-m", "video_converter"],
            schedule=schedule,
            watch_paths=[Path("/tmp/watch")],
        )
        assert config.schedule == schedule
        assert len(config.watch_paths) == 1

    def test_requires_schedule_or_watch(self) -> None:
        """Test validation requires schedule or watch_paths."""
        with pytest.raises(ValueError, match="Either schedule or watch_paths"):
            LaunchdConfig(program_args=["python"])


class TestLaunchdPlistGenerator:
    """Tests for LaunchdPlistGenerator class."""

    def test_initialization_default(self) -> None:
        """Test generator with default settings."""
        generator = LaunchdPlistGenerator()
        assert generator.module_name == "video_converter"
        assert generator.command == "run"
        assert generator.python_path.exists()

    def test_initialization_custom(self) -> None:
        """Test generator with custom settings."""
        generator = LaunchdPlistGenerator(
            module_name="custom_module",
            command="convert",
        )
        assert generator.module_name == "custom_module"
        assert generator.command == "convert"

    def test_generate_plist_daily(self) -> None:
        """Test plist generation for daily schedule."""
        generator = LaunchdPlistGenerator()
        plist = generator.generate_plist(hour=3, minute=0)

        assert plist["Label"] == SERVICE_LABEL
        assert "ProgramArguments" in plist
        assert plist["StartCalendarInterval"] == {"Hour": 3, "Minute": 0}
        assert "WatchPaths" not in plist

    def test_generate_plist_weekly(self) -> None:
        """Test plist generation for weekly schedule."""
        generator = LaunchdPlistGenerator()
        plist = generator.generate_plist(hour=9, minute=30, weekday=1)

        assert plist["StartCalendarInterval"] == {
            "Hour": 9,
            "Minute": 30,
            "Weekday": 1,
        }

    def test_generate_plist_watch_paths(self) -> None:
        """Test plist generation with watch paths."""
        generator = LaunchdPlistGenerator()
        watch_paths = [Path("~/Videos/Import")]
        plist = generator.generate_plist(hour=None, watch_paths=watch_paths)

        assert "StartCalendarInterval" not in plist
        assert "WatchPaths" in plist
        assert len(plist["WatchPaths"]) == 1
        # Path should be expanded
        assert "~" not in plist["WatchPaths"][0]

    def test_generate_plist_run_at_load(self) -> None:
        """Test plist with run_at_load enabled."""
        generator = LaunchdPlistGenerator()
        plist = generator.generate_plist(hour=3, run_at_load=True)

        assert plist["RunAtLoad"] is True

    def test_generate_plist_environment(self) -> None:
        """Test plist includes environment variables."""
        generator = LaunchdPlistGenerator()
        plist = generator.generate_plist(hour=3)

        assert "EnvironmentVariables" in plist
        env = plist["EnvironmentVariables"]
        assert "PATH" in env
        assert "PYTHONUNBUFFERED" in env
        assert "HOME" in env

    def test_generate_plist_logging(self) -> None:
        """Test plist includes log paths."""
        generator = LaunchdPlistGenerator()
        plist = generator.generate_plist(hour=3)

        assert "StandardOutPath" in plist
        assert "StandardErrorPath" in plist
        assert "stdout.log" in plist["StandardOutPath"]
        assert "stderr.log" in plist["StandardErrorPath"]

    def test_generate_plist_program_args(self) -> None:
        """Test plist program arguments structure."""
        generator = LaunchdPlistGenerator()
        plist = generator.generate_plist(hour=3)

        args = plist["ProgramArguments"]
        assert len(args) >= 4
        assert "-m" in args
        assert "video_converter" in args
        assert "run" in args

    def test_generate_plist_extra_args(self) -> None:
        """Test plist with extra command line arguments."""
        generator = LaunchdPlistGenerator()
        plist = generator.generate_plist(hour=3, extra_args=["--verbose", "--dry-run"])

        args = plist["ProgramArguments"]
        assert "--verbose" in args
        assert "--dry-run" in args

    def test_plist_to_xml(self) -> None:
        """Test conversion to XML bytes."""
        generator = LaunchdPlistGenerator()
        plist = generator.generate_plist(hour=3)
        xml_bytes = generator.plist_to_xml(plist)

        assert isinstance(xml_bytes, bytes)
        assert b"<?xml" in xml_bytes
        assert b"plist" in xml_bytes
        assert b"com.videoconverter.daily" in xml_bytes

    def test_write_plist(self) -> None:
        """Test writing plist to file."""
        generator = LaunchdPlistGenerator()
        plist = generator.generate_plist(hour=3)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.plist"
            result_path = generator.write_plist(plist, output_path)

            assert result_path == output_path
            assert output_path.exists()

            # Verify it's valid plist
            with output_path.open("rb") as f:
                loaded = plistlib.load(f)
            assert loaded["Label"] == SERVICE_LABEL

    def test_get_plist_path(self) -> None:
        """Test getting default plist path."""
        generator = LaunchdPlistGenerator()
        path = generator.get_plist_path()

        assert path.parent == DEFAULT_LAUNCH_AGENTS_DIR
        assert path.name == DEFAULT_PLIST_NAME


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_generate_daily_plist(self) -> None:
        """Test generate_daily_plist function."""
        plist = generate_daily_plist(hour=4, minute=30)

        assert plist["Label"] == SERVICE_LABEL
        assert plist["StartCalendarInterval"] == {"Hour": 4, "Minute": 30}

    def test_generate_watch_plist(self) -> None:
        """Test generate_watch_plist function."""
        plist = generate_watch_plist([Path("~/Videos/Import")])

        assert plist["Label"] == SERVICE_LABEL
        assert "WatchPaths" in plist
        assert len(plist["WatchPaths"]) == 1


class TestValidatePlistSyntax:
    """Tests for plist validation function."""

    def test_valid_plist(self) -> None:
        """Test validation of valid plist file."""
        generator = LaunchdPlistGenerator()
        plist = generator.generate_plist(hour=3)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.plist"
            generator.write_plist(plist, output_path)

            assert validate_plist_syntax(output_path) is True

    def test_invalid_plist(self) -> None:
        """Test validation of invalid plist file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "invalid.plist"
            output_path.write_text("not valid xml")

            assert validate_plist_syntax(output_path) is False


class TestConstants:
    """Tests for module constants."""

    def test_default_launch_agents_dir(self) -> None:
        """Test default LaunchAgents directory."""
        assert DEFAULT_LAUNCH_AGENTS_DIR.name == "LaunchAgents"
        assert "Library" in str(DEFAULT_LAUNCH_AGENTS_DIR)

    def test_default_plist_name(self) -> None:
        """Test default plist filename."""
        assert DEFAULT_PLIST_NAME.endswith(".plist")
        assert "videoconverter" in DEFAULT_PLIST_NAME

    def test_default_log_dir(self) -> None:
        """Test default log directory."""
        assert "Logs" in str(DEFAULT_LOG_DIR)
        assert "video_converter" in str(DEFAULT_LOG_DIR)

    def test_service_label(self) -> None:
        """Test service label format."""
        assert SERVICE_LABEL.startswith("com.")
        assert "videoconverter" in SERVICE_LABEL
