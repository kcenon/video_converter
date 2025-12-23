"""Core module for video conversion workflow.

This module provides the central orchestration and type definitions
for the video conversion pipeline.

Note:
    To avoid circular imports, Orchestrator is imported separately:
    >>> from video_converter.core.orchestrator import Orchestrator
"""

from video_converter.core.concurrent import (
    AggregatedProgress,
    ConcurrentProcessor,
    JobProgress,
    ResourceLevel,
    ResourceMonitor,
    ResourceStatus,
)
from video_converter.core.config import (
    AutomationConfig,
    Config,
    EncodingConfig,
    NotificationConfig,
    PathsConfig,
    PhotosConfig,
    ProcessingConfig,
)
from video_converter.core.error_recovery import (
    DEFAULT_MIN_FREE_SPACE,
    ERROR_RECOVERY_MAPPING,
    DiskSpaceInfo,
    ErrorRecoveryManager,
    FailureRecord,
)
from video_converter.core.history import (
    ConversionHistory,
    ConversionRecord,
    HistoryCorruptedError,
    HistoryError,
    HistoryStatistics,
    get_history,
    reset_history,
)
from video_converter.core.logger import (
    LogLevel,
    configure_logging,
    get_log_dir,
    get_log_file_path,
    get_logger,
    set_log_level,
)
from video_converter.core.session import (
    SessionCorruptedError,
    SessionNotFoundError,
    SessionStateError,
    SessionStateManager,
    get_session_manager,
)
from video_converter.core.types import (
    BatchStatus,
    CompleteCallback,
    ConversionMode,
    ConversionProgress,
    ConversionReport,
    ConversionRequest,
    ConversionResult,
    ConversionStage,
    ConversionStatus,
    ErrorCategory,
    ProgressCallback,
    QueuePriority,
    RecoveryAction,
    SessionState,
    SessionStatus,
    VideoEntry,
)

__all__ = [
    # Config
    "AutomationConfig",
    "Config",
    "EncodingConfig",
    "NotificationConfig",
    "PathsConfig",
    "PhotosConfig",
    "ProcessingConfig",
    # Concurrent
    "AggregatedProgress",
    "ConcurrentProcessor",
    "JobProgress",
    "ResourceLevel",
    "ResourceMonitor",
    "ResourceStatus",
    # Error Recovery
    "DEFAULT_MIN_FREE_SPACE",
    "DiskSpaceInfo",
    "ERROR_RECOVERY_MAPPING",
    "ErrorCategory",
    "ErrorRecoveryManager",
    "FailureRecord",
    "RecoveryAction",
    # History
    "ConversionHistory",
    "ConversionRecord",
    "get_history",
    "HistoryCorruptedError",
    "HistoryError",
    "HistoryStatistics",
    "reset_history",
    # Logger
    "configure_logging",
    "get_log_dir",
    "get_log_file_path",
    "get_logger",
    "LogLevel",
    "set_log_level",
    # Session
    "get_session_manager",
    "SessionCorruptedError",
    "SessionNotFoundError",
    "SessionState",
    "SessionStateError",
    "SessionStateManager",
    "SessionStatus",
    "VideoEntry",
    # Types
    "BatchStatus",
    "CompleteCallback",
    "ConversionMode",
    "ConversionProgress",
    "ConversionReport",
    "ConversionRequest",
    "ConversionResult",
    "ConversionStage",
    "ConversionStatus",
    "ProgressCallback",
    "QueuePriority",
]


def __getattr__(name: str):
    """Lazy import for Orchestrator to avoid circular imports."""
    if name in ("Orchestrator", "OrchestratorConfig", "ConversionTask"):
        from video_converter.core.orchestrator import (
            ConversionTask,
            Orchestrator,
            OrchestratorConfig,
        )

        return {
            "Orchestrator": Orchestrator,
            "OrchestratorConfig": OrchestratorConfig,
            "ConversionTask": ConversionTask,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
