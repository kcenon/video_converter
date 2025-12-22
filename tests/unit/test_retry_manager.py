"""Unit tests for retry_manager module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from video_converter.core.types import ConversionMode, ConversionRequest, ConversionResult
from video_converter.processors.retry_manager import (
    FailureType,
    RetryAttempt,
    RetryConfig,
    RetryManager,
    RetryResult,
    RetryStrategy,
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 4
        assert config.switch_encoder_on_failure is True
        assert config.adjust_quality_on_failure is True
        assert config.quality_adjustment_step == 2
        assert config.max_crf_value == 28
        assert config.preserve_original_on_failure is True

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=3,
            switch_encoder_on_failure=False,
            quality_adjustment_step=4,
        )
        assert config.max_attempts == 3
        assert config.switch_encoder_on_failure is False
        assert config.quality_adjustment_step == 4

    def test_invalid_max_attempts(self) -> None:
        """Test that max_attempts must be at least 1."""
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            RetryConfig(max_attempts=0)

    def test_invalid_quality_step(self) -> None:
        """Test that quality_adjustment_step must be positive."""
        with pytest.raises(ValueError, match="quality_adjustment_step must be positive"):
            RetryConfig(quality_adjustment_step=0)


class TestRetryAttempt:
    """Tests for RetryAttempt dataclass."""

    def test_attempt_creation(self) -> None:
        """Test creating a retry attempt record."""
        attempt = RetryAttempt(
            attempt_number=1,
            strategy=RetryStrategy.SAME_SETTINGS,
            mode=ConversionMode.HARDWARE,
            crf=22,
        )
        assert attempt.attempt_number == 1
        assert attempt.strategy == RetryStrategy.SAME_SETTINGS
        assert attempt.mode == ConversionMode.HARDWARE
        assert attempt.crf == 22
        assert attempt.error_message is None

    def test_attempt_with_failure(self) -> None:
        """Test attempt record with failure information."""
        attempt = RetryAttempt(
            attempt_number=2,
            strategy=RetryStrategy.SWITCH_ENCODER,
            mode=ConversionMode.SOFTWARE,
            crf=22,
            error_message="Encoder failed",
            failure_type=FailureType.ENCODER_ERROR,
        )
        assert attempt.error_message == "Encoder failed"
        assert attempt.failure_type == FailureType.ENCODER_ERROR

    def test_attempt_to_dict(self) -> None:
        """Test converting attempt to dictionary."""
        now = datetime.now()
        attempt = RetryAttempt(
            attempt_number=1,
            strategy=RetryStrategy.SAME_SETTINGS,
            mode=ConversionMode.HARDWARE,
            crf=22,
            started_at=now,
            completed_at=now,
            duration_seconds=10.5,
        )
        data = attempt.to_dict()
        assert data["attempt_number"] == 1
        assert data["strategy"] == "same_settings"
        assert data["mode"] == "hardware"
        assert data["crf"] == 22
        assert data["duration_seconds"] == 10.5


class TestRetryResult:
    """Tests for RetryResult dataclass."""

    def test_successful_result(self) -> None:
        """Test successful retry result."""
        result = RetryResult(
            success=True,
            total_attempts=2,
            final_strategy=RetryStrategy.SWITCH_ENCODER,
        )
        assert result.success is True
        assert result.total_attempts == 2
        assert result.original_preserved is True

    def test_failed_result(self) -> None:
        """Test failed retry result."""
        attempts = [
            RetryAttempt(1, RetryStrategy.SAME_SETTINGS, ConversionMode.HARDWARE, 22, "Error 1"),
            RetryAttempt(2, RetryStrategy.SAME_SETTINGS, ConversionMode.HARDWARE, 22, "Error 2"),
        ]
        result = RetryResult(
            success=False,
            attempts=attempts,
            total_attempts=2,
        )
        assert result.success is False
        assert len(result.attempts) == 2

    def test_failure_report_success(self) -> None:
        """Test failure report for successful conversion."""
        result = RetryResult(success=True, total_attempts=1)
        report = result.get_failure_report()
        assert "Succeeded after 1 attempt" in report

    def test_failure_report_failure(self) -> None:
        """Test failure report for failed conversion."""
        attempts = [
            RetryAttempt(
                1, RetryStrategy.SAME_SETTINGS, ConversionMode.HARDWARE, 22,
                error_message="Encoder not available",
            ),
        ]
        result = RetryResult(
            success=False,
            attempts=attempts,
            total_attempts=1,
            original_preserved=True,
        )
        report = result.get_failure_report()
        assert "Failed after 1 attempt" in report
        assert "Encoder not available" in report
        assert "Original file preserved" in report

    def test_to_dict(self) -> None:
        """Test converting result to dictionary."""
        result = RetryResult(
            success=True,
            total_attempts=3,
            final_strategy=RetryStrategy.ADJUST_QUALITY,
            total_duration_seconds=45.5,
        )
        data = result.to_dict()
        assert data["success"] is True
        assert data["total_attempts"] == 3
        assert data["final_strategy"] == "adjust_quality"
        assert data["total_duration_seconds"] == 45.5


class TestRetryManager:
    """Tests for RetryManager class."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        manager = RetryManager()
        assert manager.config.max_attempts == 4

    def test_custom_config_initialization(self) -> None:
        """Test initialization with custom config."""
        config = RetryConfig(max_attempts=2)
        manager = RetryManager(config)
        assert manager.config.max_attempts == 2

    def test_determine_strategy_first_attempt(self) -> None:
        """Test strategy determination for first attempt."""
        manager = RetryManager()
        strategy = manager._determine_strategy(1, None)
        assert strategy == RetryStrategy.SAME_SETTINGS

    def test_determine_strategy_second_attempt(self) -> None:
        """Test strategy determination for second attempt."""
        manager = RetryManager()
        strategy = manager._determine_strategy(2, FailureType.CONVERSION_ERROR)
        assert strategy == RetryStrategy.SAME_SETTINGS

    def test_determine_strategy_third_attempt_switch_encoder(self) -> None:
        """Test strategy determination for third attempt - switch encoder."""
        manager = RetryManager()
        strategy = manager._determine_strategy(3, FailureType.ENCODER_ERROR)
        assert strategy == RetryStrategy.SWITCH_ENCODER

    def test_determine_strategy_fourth_attempt_adjust_quality(self) -> None:
        """Test strategy determination for fourth attempt - adjust quality."""
        manager = RetryManager()
        strategy = manager._determine_strategy(4, FailureType.COMPRESSION_ERROR)
        assert strategy == RetryStrategy.ADJUST_QUALITY

    def test_determine_strategy_disabled_switch_encoder(self) -> None:
        """Test strategy when switch encoder is disabled."""
        config = RetryConfig(switch_encoder_on_failure=False)
        manager = RetryManager(config)
        strategy = manager._determine_strategy(3, FailureType.ENCODER_ERROR)
        assert strategy == RetryStrategy.FINAL_ATTEMPT

    def test_classify_failure_encoder_error(self) -> None:
        """Test failure classification for encoder errors."""
        manager = RetryManager()
        result = ConversionResult(
            success=False,
            request=MagicMock(),
            error_message="VideoToolbox encoder failed",
        )
        failure_type = manager._classify_failure(result, None)
        assert failure_type == FailureType.ENCODER_ERROR

    def test_classify_failure_validation_error(self) -> None:
        """Test failure classification for validation errors."""
        manager = RetryManager()
        result = ConversionResult(success=True, request=MagicMock())
        validation = MagicMock()
        validation.valid = False
        validation.errors = ["No video stream found"]
        failure_type = manager._classify_failure(result, validation)
        assert failure_type == FailureType.VALIDATION_ERROR

    def test_classify_failure_compression_error(self) -> None:
        """Test failure classification for compression errors."""
        manager = RetryManager()
        result = ConversionResult(success=True, request=MagicMock())
        validation = MagicMock()
        validation.valid = False
        validation.errors = ["File size compression ratio too low"]
        failure_type = manager._classify_failure(result, validation)
        assert failure_type == FailureType.COMPRESSION_ERROR

    def test_adjust_request_same_settings(self) -> None:
        """Test request adjustment with same settings strategy."""
        manager = RetryManager()
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            mode=ConversionMode.HARDWARE,
            crf=22,
        )
        adjusted, mode, crf = manager._adjust_request(
            request, RetryStrategy.SAME_SETTINGS, ConversionMode.HARDWARE, 22
        )
        assert mode == ConversionMode.HARDWARE
        assert crf == 22

    def test_adjust_request_switch_encoder_hw_to_sw(self) -> None:
        """Test request adjustment switching from hardware to software."""
        manager = RetryManager()
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            mode=ConversionMode.HARDWARE,
            crf=22,
        )
        adjusted, mode, crf = manager._adjust_request(
            request, RetryStrategy.SWITCH_ENCODER, ConversionMode.HARDWARE, 22
        )
        assert mode == ConversionMode.SOFTWARE
        assert adjusted.mode == ConversionMode.SOFTWARE

    def test_adjust_request_switch_encoder_sw_to_hw(self) -> None:
        """Test request adjustment switching from software to hardware."""
        manager = RetryManager()
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            mode=ConversionMode.SOFTWARE,
            crf=22,
        )
        adjusted, mode, crf = manager._adjust_request(
            request, RetryStrategy.SWITCH_ENCODER, ConversionMode.SOFTWARE, 22
        )
        assert mode == ConversionMode.HARDWARE
        assert adjusted.mode == ConversionMode.HARDWARE

    def test_adjust_request_adjust_quality(self) -> None:
        """Test request adjustment for quality adjustment strategy."""
        manager = RetryManager()
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            mode=ConversionMode.HARDWARE,
            crf=22,
        )
        adjusted, mode, crf = manager._adjust_request(
            request, RetryStrategy.ADJUST_QUALITY, ConversionMode.HARDWARE, 22
        )
        assert crf == 24  # 22 + 2 (default step)
        assert adjusted.crf == 24

    def test_adjust_request_quality_max_crf(self) -> None:
        """Test that CRF does not exceed max value."""
        config = RetryConfig(max_crf_value=25)
        manager = RetryManager(config)
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            mode=ConversionMode.HARDWARE,
            crf=24,
        )
        adjusted, mode, crf = manager._adjust_request(
            request, RetryStrategy.ADJUST_QUALITY, ConversionMode.HARDWARE, 24
        )
        assert crf == 25  # Capped at max


class TestRetryManagerAsync:
    """Async tests for RetryManager."""

    @pytest.fixture
    def mock_converter(self) -> MagicMock:
        """Create a mock converter."""
        converter = MagicMock()
        converter.convert = AsyncMock()
        return converter

    @pytest.fixture
    def mock_factory(self, mock_converter: MagicMock) -> MagicMock:
        """Create a mock converter factory."""
        factory = MagicMock()
        factory.get_converter.return_value = mock_converter
        return factory

    @pytest.fixture
    def sample_request(self, tmp_path: Path) -> ConversionRequest:
        """Create a sample conversion request."""
        input_path = tmp_path / "input.mov"
        input_path.touch()
        output_path = tmp_path / "output.mp4"
        return ConversionRequest(
            input_path=input_path,
            output_path=output_path,
            mode=ConversionMode.HARDWARE,
            crf=22,
        )

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_attempt(
        self,
        mock_factory: MagicMock,
        mock_converter: MagicMock,
        sample_request: ConversionRequest,
    ) -> None:
        """Test successful conversion on first attempt."""
        mock_converter.convert.return_value = ConversionResult(
            success=True,
            request=sample_request,
            original_size=100_000_000,
            converted_size=50_000_000,
        )

        manager = RetryManager()
        result = await manager.execute_with_retry(
            request=sample_request,
            converter_factory=mock_factory,
        )

        assert result.success is True
        assert result.total_attempts == 1
        assert result.final_strategy == RetryStrategy.SAME_SETTINGS

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_retry(
        self,
        mock_factory: MagicMock,
        mock_converter: MagicMock,
        sample_request: ConversionRequest,
    ) -> None:
        """Test successful conversion after one retry."""
        mock_converter.convert.side_effect = [
            ConversionResult(
                success=False,
                request=sample_request,
                error_message="Temporary failure",
            ),
            ConversionResult(
                success=True,
                request=sample_request,
                original_size=100_000_000,
                converted_size=50_000_000,
            ),
        ]

        manager = RetryManager()
        result = await manager.execute_with_retry(
            request=sample_request,
            converter_factory=mock_factory,
        )

        assert result.success is True
        assert result.total_attempts == 2
        assert len(result.attempts) == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_all_attempts_fail(
        self,
        mock_factory: MagicMock,
        mock_converter: MagicMock,
        sample_request: ConversionRequest,
    ) -> None:
        """Test when all retry attempts fail."""
        mock_converter.convert.return_value = ConversionResult(
            success=False,
            request=sample_request,
            error_message="Persistent failure",
        )

        config = RetryConfig(max_attempts=3)
        manager = RetryManager(config)
        result = await manager.execute_with_retry(
            request=sample_request,
            converter_factory=mock_factory,
        )

        assert result.success is False
        assert result.total_attempts == 3
        assert len(result.attempts) == 3
        assert result.original_preserved is True

    @pytest.mark.asyncio
    async def test_execute_with_retry_encoder_switch(
        self,
        mock_factory: MagicMock,
        sample_request: ConversionRequest,
    ) -> None:
        """Test that encoder switching is attempted on third try."""
        hw_converter = MagicMock()
        hw_converter.convert = AsyncMock(
            return_value=ConversionResult(
                success=False,
                request=sample_request,
                error_message="VideoToolbox encoder failed",
            )
        )

        sw_converter = MagicMock()
        sw_converter.convert = AsyncMock(
            return_value=ConversionResult(
                success=True,
                request=sample_request,
                original_size=100_000_000,
                converted_size=50_000_000,
            )
        )

        call_count = 0

        def get_converter_side_effect(mode, fallback=True):
            nonlocal call_count
            call_count += 1
            if mode == ConversionMode.SOFTWARE:
                return sw_converter
            return hw_converter

        mock_factory.get_converter.side_effect = get_converter_side_effect

        manager = RetryManager()
        result = await manager.execute_with_retry(
            request=sample_request,
            converter_factory=mock_factory,
        )

        assert result.success is True
        assert result.total_attempts == 3
        assert result.final_strategy == RetryStrategy.SWITCH_ENCODER

    @pytest.mark.asyncio
    async def test_execute_with_retry_with_validator(
        self,
        mock_factory: MagicMock,
        mock_converter: MagicMock,
        sample_request: ConversionRequest,
    ) -> None:
        """Test retry with validation."""
        mock_converter.convert.return_value = ConversionResult(
            success=True,
            request=sample_request,
        )

        mock_validator = MagicMock()
        validation_result = MagicMock()
        validation_result.valid = True
        validation_result.errors = []
        validation_result.warnings = []
        mock_validator.validate.return_value = validation_result

        manager = RetryManager()
        result = await manager.execute_with_retry(
            request=sample_request,
            converter_factory=mock_factory,
            validator=mock_validator,
        )

        assert result.success is True
        mock_validator.validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_retry_validation_failure_triggers_retry(
        self,
        mock_factory: MagicMock,
        sample_request: ConversionRequest,
    ) -> None:
        """Test that validation failure triggers retry."""
        # Create converter that returns fresh ConversionResult each time
        mock_converter = MagicMock()

        def create_success_result(*args, **kwargs):
            return ConversionResult(
                success=True,
                request=sample_request,
            )

        mock_converter.convert = AsyncMock(side_effect=create_success_result)
        mock_factory.get_converter.return_value = mock_converter

        mock_validator = MagicMock()
        failed_validation = MagicMock()
        failed_validation.valid = False
        failed_validation.errors = ["Invalid video stream"]
        failed_validation.warnings = []

        success_validation = MagicMock()
        success_validation.valid = True
        success_validation.errors = []
        success_validation.warnings = []

        # Provide enough validation responses for all potential attempts
        mock_validator.validate.side_effect = [
            failed_validation,  # First attempt fails validation
            success_validation,  # Second attempt passes validation
        ]

        config = RetryConfig(max_attempts=2)
        manager = RetryManager(config)
        result = await manager.execute_with_retry(
            request=sample_request,
            converter_factory=mock_factory,
            validator=mock_validator,
        )

        assert result.success is True
        assert result.total_attempts == 2
        assert mock_validator.validate.call_count == 2


class TestRetryStrategy:
    """Tests for RetryStrategy enum."""

    def test_strategy_values(self) -> None:
        """Test strategy enum values."""
        assert RetryStrategy.SAME_SETTINGS.value == "same_settings"
        assert RetryStrategy.SWITCH_ENCODER.value == "switch_encoder"
        assert RetryStrategy.ADJUST_QUALITY.value == "adjust_quality"
        assert RetryStrategy.FINAL_ATTEMPT.value == "final_attempt"


class TestFailureType:
    """Tests for FailureType enum."""

    def test_failure_type_values(self) -> None:
        """Test failure type enum values."""
        assert FailureType.CONVERSION_ERROR.value == "conversion_error"
        assert FailureType.VALIDATION_ERROR.value == "validation_error"
        assert FailureType.COMPRESSION_ERROR.value == "compression_error"
        assert FailureType.ENCODER_ERROR.value == "encoder_error"
        assert FailureType.VMAF_QUALITY_ERROR.value == "vmaf_quality_error"
        assert FailureType.UNKNOWN.value == "unknown"

    def test_vmaf_quality_error_type(self) -> None:
        """Test VMAF quality error type for low quality conversions."""
        assert FailureType.VMAF_QUALITY_ERROR in FailureType
        assert FailureType.VMAF_QUALITY_ERROR.value == "vmaf_quality_error"
