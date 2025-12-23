"""Validation retry logic for failed conversions.

This module provides retry logic for conversions that fail validation,
with configurable retry attempts and fallback strategies.

SDS Reference: SDS-P05-004
SRS Reference: SRS-504 (Validation Retry Logic)

Retry Strategy:
    1. First failure: Retry with same settings
    2. Second failure: Switch encoder (HW→SW or vice versa)
    3. Third failure: Adjust quality settings (increase CRF)
    4. Final failure: Mark as failed, preserve original

Example:
    >>> from video_converter.processors.retry_manager import RetryManager
    >>> from video_converter.core import ConversionRequest
    >>>
    >>> retry_manager = RetryManager()
    >>> result = await retry_manager.execute_with_retry(
    ...     request=request,
    ...     converter_factory=factory,
    ...     validator=validator,
    ... )
    >>> if result.success:
    ...     print(f"Succeeded after {result.total_attempts} attempts")
    ... else:
    ...     print(f"Failed after {result.total_attempts} attempts")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from video_converter.core.types import (
    ConversionMode,
    ConversionRequest,
    ConversionResult,
)

if TYPE_CHECKING:
    from video_converter.converters.factory import ConverterFactory
    from video_converter.processors.quality_validator import (
        ValidationResult,
        VideoValidator,
    )

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Strategy used for a retry attempt.

    Attributes:
        SAME_SETTINGS: Retry with identical settings.
        SWITCH_ENCODER: Switch between hardware and software encoder.
        ADJUST_QUALITY: Lower quality requirements (increase CRF).
        FINAL_ATTEMPT: Last attempt before giving up.
    """

    SAME_SETTINGS = "same_settings"
    SWITCH_ENCODER = "switch_encoder"
    ADJUST_QUALITY = "adjust_quality"
    FINAL_ATTEMPT = "final_attempt"


class FailureType(Enum):
    """Type of failure that triggered retry.

    Attributes:
        CONVERSION_ERROR: FFmpeg conversion failed.
        VALIDATION_ERROR: Output file failed validation.
        COMPRESSION_ERROR: Compression ratio out of expected range.
        ENCODER_ERROR: Hardware/software encoder not available.
        VMAF_QUALITY_ERROR: VMAF score below acceptable threshold.
        UNKNOWN: Unknown error type.
    """

    CONVERSION_ERROR = "conversion_error"
    VALIDATION_ERROR = "validation_error"
    COMPRESSION_ERROR = "compression_error"
    ENCODER_ERROR = "encoder_error"
    VMAF_QUALITY_ERROR = "vmaf_quality_error"
    UNKNOWN = "unknown"


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts (default: 4).
        switch_encoder_on_failure: Whether to try alternate encoder.
        adjust_quality_on_failure: Whether to adjust quality settings.
        quality_adjustment_step: CRF increase per quality adjustment.
        max_crf_value: Maximum CRF value to try before giving up.
        preserve_original_on_failure: Keep original file on final failure.
    """

    max_attempts: int = 4
    switch_encoder_on_failure: bool = True
    adjust_quality_on_failure: bool = True
    quality_adjustment_step: int = 2
    max_crf_value: int = 28
    preserve_original_on_failure: bool = True

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.quality_adjustment_step < 1:
            raise ValueError("quality_adjustment_step must be positive")


@dataclass
class RetryAttempt:
    """Record of a single retry attempt.

    Attributes:
        attempt_number: Which attempt this was (1-based).
        strategy: The strategy used for this attempt.
        mode: Conversion mode used (hardware/software).
        crf: CRF value used for this attempt.
        error_message: Error message if attempt failed.
        failure_type: Type of failure encountered.
        started_at: When the attempt started.
        completed_at: When the attempt finished.
        duration_seconds: Time taken for this attempt.
    """

    attempt_number: int
    strategy: RetryStrategy
    mode: ConversionMode
    crf: int
    error_message: str | None = None
    failure_type: FailureType | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "attempt_number": self.attempt_number,
            "strategy": self.strategy.value,
            "mode": self.mode.value,
            "crf": self.crf,
            "error_message": self.error_message,
            "failure_type": self.failure_type.value if self.failure_type else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class RetryResult:
    """Result of retry execution.

    Attributes:
        success: Whether conversion ultimately succeeded.
        final_result: The final ConversionResult.
        attempts: List of all retry attempts made.
        total_attempts: Total number of attempts.
        final_strategy: The strategy that succeeded (or last tried).
        total_duration_seconds: Total time across all attempts.
        original_preserved: Whether original file was preserved.
    """

    success: bool
    final_result: ConversionResult | None = None
    attempts: list[RetryAttempt] = field(default_factory=list)
    total_attempts: int = 0
    final_strategy: RetryStrategy | None = None
    total_duration_seconds: float = 0.0
    original_preserved: bool = True

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "success": self.success,
            "total_attempts": self.total_attempts,
            "final_strategy": self.final_strategy.value if self.final_strategy else None,
            "total_duration_seconds": self.total_duration_seconds,
            "original_preserved": self.original_preserved,
            "attempts": [a.to_dict() for a in self.attempts],
        }

    def get_failure_report(self) -> str:
        """Generate a human-readable failure report.

        Returns:
            Formatted string describing all retry attempts.
        """
        if self.success:
            return f"Succeeded after {self.total_attempts} attempt(s)"

        lines = [
            f"Failed after {self.total_attempts} attempt(s):",
            "",
        ]

        for attempt in self.attempts:
            status = "FAILED" if attempt.error_message else "OK"
            lines.append(
                f"  Attempt {attempt.attempt_number}: {attempt.strategy.value} "
                f"(mode={attempt.mode.value}, crf={attempt.crf}) - {status}"
            )
            if attempt.error_message:
                lines.append(f"    Error: {attempt.error_message}")

        if self.original_preserved:
            lines.append("")
            lines.append("  Original file preserved.")

        return "\n".join(lines)


class RetryManager:
    """Manage retry logic for failed conversions.

    This class implements a configurable retry strategy for video conversions
    that fail validation. It supports:
    - Retrying with same settings
    - Switching between hardware and software encoders
    - Adjusting quality settings to improve success rate
    - Tracking all retry attempts for reporting

    SDS Reference: SDS-P05-004
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        """Initialize the retry manager.

        Args:
            config: Retry configuration. Uses defaults if None.
        """
        self.config = config or RetryConfig()

    def _determine_strategy(
        self,
        attempt_number: int,
        previous_failure: FailureType | None,
    ) -> RetryStrategy:
        """Determine which retry strategy to use.

        Args:
            attempt_number: Current attempt number (1-based).
            previous_failure: Type of previous failure.

        Returns:
            The retry strategy to use for this attempt.
        """
        if attempt_number == 1:
            return RetryStrategy.SAME_SETTINGS

        if attempt_number == 2:
            return RetryStrategy.SAME_SETTINGS

        if attempt_number == 3 and self.config.switch_encoder_on_failure:
            return RetryStrategy.SWITCH_ENCODER

        if attempt_number == 4 and self.config.adjust_quality_on_failure:
            return RetryStrategy.ADJUST_QUALITY

        return RetryStrategy.FINAL_ATTEMPT

    def _classify_failure(
        self,
        result: ConversionResult,
        validation: ValidationResult | None,
    ) -> FailureType:
        """Classify the type of failure.

        Args:
            result: The conversion result.
            validation: The validation result (if any).

        Returns:
            The classified failure type.
        """
        error_msg = (result.error_message or "").lower()

        if "encoder" in error_msg or "videotoolbox" in error_msg:
            return FailureType.ENCODER_ERROR

        if validation and not validation.valid:
            if validation.errors:
                error_text = " ".join(validation.errors).lower()
                if "compression" in error_text or "size" in error_text:
                    return FailureType.COMPRESSION_ERROR
            return FailureType.VALIDATION_ERROR

        if not result.success:
            return FailureType.CONVERSION_ERROR

        return FailureType.UNKNOWN

    def _adjust_request(
        self,
        request: ConversionRequest,
        strategy: RetryStrategy,
        current_mode: ConversionMode,
        current_crf: int,
    ) -> tuple[ConversionRequest, ConversionMode, int]:
        """Create adjusted request based on retry strategy.

        Args:
            request: Original conversion request.
            strategy: Retry strategy to apply.
            current_mode: Current conversion mode.
            current_crf: Current CRF value.

        Returns:
            Tuple of (adjusted_request, new_mode, new_crf).
        """
        new_mode = current_mode
        new_crf = current_crf

        if strategy == RetryStrategy.SWITCH_ENCODER:
            if current_mode == ConversionMode.HARDWARE:
                new_mode = ConversionMode.SOFTWARE
            else:
                new_mode = ConversionMode.HARDWARE
            logger.info(f"Switching encoder from {current_mode.value} to {new_mode.value}")

        elif strategy == RetryStrategy.ADJUST_QUALITY:
            new_crf = min(
                current_crf + self.config.quality_adjustment_step,
                self.config.max_crf_value,
            )
            logger.info(f"Adjusting quality: CRF {current_crf} -> {new_crf}")

        adjusted = ConversionRequest(
            input_path=request.input_path,
            output_path=request.output_path,
            mode=new_mode,
            quality=request.quality,
            crf=new_crf,
            preset=request.preset,
            audio_mode=request.audio_mode,
            preserve_metadata=request.preserve_metadata,
            bit_depth=request.bit_depth,
            hdr=request.hdr,
        )

        return adjusted, new_mode, new_crf

    def _cleanup_failed_output(self, output_path: Path) -> None:
        """Clean up failed conversion output.

        Args:
            output_path: Path to the output file to remove.
        """
        if output_path.exists():
            try:
                output_path.unlink()
                logger.debug(f"Removed failed output: {output_path}")
            except OSError as e:
                logger.warning(f"Could not remove failed output: {e}")

    async def execute_with_retry(
        self,
        request: ConversionRequest,
        converter_factory: ConverterFactory,
        validator: VideoValidator | None = None,
    ) -> RetryResult:
        """Execute conversion with automatic retry on failure.

        This method attempts the conversion and automatically retries
        with different strategies if it fails.

        Args:
            request: The conversion request.
            converter_factory: Factory for getting converters.
            validator: Optional validator for checking output.

        Returns:
            RetryResult containing success status and all attempt details.
        """
        result = RetryResult(success=False)
        current_mode = request.mode
        current_crf = request.crf
        previous_failure: FailureType | None = None
        current_request = request

        for attempt_num in range(1, self.config.max_attempts + 1):
            strategy = self._determine_strategy(attempt_num, previous_failure)

            if attempt_num > 1:
                current_request, current_mode, current_crf = self._adjust_request(
                    request,
                    strategy,
                    current_mode,
                    current_crf,
                )

            attempt = RetryAttempt(
                attempt_number=attempt_num,
                strategy=strategy,
                mode=current_mode,
                crf=current_crf,
                started_at=datetime.now(),
            )

            logger.info(
                f"Attempt {attempt_num}/{self.config.max_attempts}: "
                f"strategy={strategy.value}, mode={current_mode.value}, crf={current_crf}"
            )

            try:
                converter = converter_factory.get_converter(
                    mode=current_mode,
                    fallback=True,
                )
                conversion_result = await converter.convert(current_request)
            except Exception as e:
                conversion_result = ConversionResult(
                    success=False,
                    request=current_request,
                    error_message=str(e),
                )

            attempt.completed_at = datetime.now()
            if attempt.started_at:
                attempt.duration_seconds = (
                    attempt.completed_at - attempt.started_at
                ).total_seconds()

            validation_result = None
            if conversion_result.success and validator:
                validation_result = validator.validate(current_request.output_path)
                if not validation_result.valid:
                    conversion_result.success = False
                    conversion_result.error_message = (
                        f"Validation failed: {', '.join(validation_result.errors)}"
                    )
                    conversion_result.warnings.extend(validation_result.warnings)

            if conversion_result.success:
                attempt.error_message = None
                attempt.failure_type = None
                result.attempts.append(attempt)
                result.success = True
                result.final_result = conversion_result
                result.total_attempts = attempt_num
                result.final_strategy = strategy
                result.total_duration_seconds = sum(a.duration_seconds for a in result.attempts)

                logger.info(
                    f"Conversion succeeded on attempt {attempt_num} with strategy {strategy.value}"
                )
                return result

            failure_type = self._classify_failure(conversion_result, validation_result)
            attempt.error_message = conversion_result.error_message
            attempt.failure_type = failure_type
            previous_failure = failure_type
            result.attempts.append(attempt)

            self._cleanup_failed_output(current_request.output_path)

            logger.warning(
                f"Attempt {attempt_num} failed: {failure_type.value} - "
                f"{conversion_result.error_message}"
            )

        result.success = False
        result.final_result = conversion_result
        result.total_attempts = len(result.attempts)
        result.final_strategy = result.attempts[-1].strategy if result.attempts else None
        result.total_duration_seconds = sum(a.duration_seconds for a in result.attempts)
        result.original_preserved = self.config.preserve_original_on_failure

        logger.error(
            f"All {self.config.max_attempts} retry attempts failed for {request.input_path.name}"
        )

        return result

    def execute_with_retry_sync(
        self,
        request: ConversionRequest,
        converter_factory: ConverterFactory,
        validator: VideoValidator | None = None,
    ) -> RetryResult:
        """Synchronous wrapper for execute_with_retry.

        Args:
            request: The conversion request.
            converter_factory: Factory for getting converters.
            validator: Optional validator for checking output.

        Returns:
            RetryResult containing success status and all attempt details.
        """
        import asyncio

        return asyncio.run(self.execute_with_retry(request, converter_factory, validator))


__all__ = [
    "RetryManager",
    "RetryConfig",
    "RetryStrategy",
    "RetryAttempt",
    "RetryResult",
    "FailureType",
]
