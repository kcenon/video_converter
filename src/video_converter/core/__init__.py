"""Core module for video conversion workflow.

This module provides the central orchestration and type definitions
for the video conversion pipeline.

Note:
    To avoid circular imports, Orchestrator is imported separately:
    >>> from video_converter.core.orchestrator import Orchestrator
"""

from video_converter.core.types import (
    CompleteCallback,
    ConversionMode,
    ConversionProgress,
    ConversionReport,
    ConversionRequest,
    ConversionResult,
    ConversionStage,
    ConversionStatus,
    ProgressCallback,
)

__all__ = [
    "CompleteCallback",
    "ConversionMode",
    "ConversionProgress",
    "ConversionReport",
    "ConversionRequest",
    "ConversionResult",
    "ConversionStage",
    "ConversionStatus",
    "ProgressCallback",
]


def __getattr__(name: str):
    """Lazy import for Orchestrator to avoid circular imports."""
    if name in ("Orchestrator", "OrchestratorConfig", "ConversionTask"):
        from video_converter.core.orchestrator import (
            ConversionTask,
            Orchestrator,
            OrchestratorConfig,
        )
        return {"Orchestrator": Orchestrator,
                "OrchestratorConfig": OrchestratorConfig,
                "ConversionTask": ConversionTask}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
