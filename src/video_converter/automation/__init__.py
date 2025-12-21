"""Automation module for scheduled video conversion.

This module provides tools for setting up automated video conversion
on macOS using launchd services.
"""

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
from video_converter.automation.service_manager import (
    ServiceManager,
    ServiceResult,
    ServiceState,
    ServiceStatus,
)

__all__ = [
    # launchd module
    "LaunchdSchedule",
    "LaunchdConfig",
    "LaunchdPlistGenerator",
    "validate_plist_syntax",
    "generate_daily_plist",
    "generate_watch_plist",
    "DEFAULT_LAUNCH_AGENTS_DIR",
    "DEFAULT_PLIST_NAME",
    "DEFAULT_LOG_DIR",
    "SERVICE_LABEL",
    # service_manager module
    "ServiceManager",
    "ServiceResult",
    "ServiceState",
    "ServiceStatus",
]
