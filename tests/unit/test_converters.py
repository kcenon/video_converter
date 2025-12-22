"""Unit tests for converters module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from video_converter.converters.base import (
    BaseConverter,
    ConversionError,
    EncoderNotAvailableError,
)
from video_converter.converters.factory import ConverterFactory, get_converter
from video_converter.converters.hardware import HardwareConverter
from video_converter.converters.software import SoftwareConverter
from video_converter.core.types import ConversionMode, ConversionRequest


class TestHardwareConverter:
    """Tests for HardwareConverter."""

    def test_encoder_name(self) -> None:
        """Test encoder name is correct."""
        converter = HardwareConverter()
        assert converter.encoder_name == "hevc_videotoolbox"

    def test_mode_is_hardware(self) -> None:
        """Test mode is HARDWARE."""
        converter = HardwareConverter()
        assert converter.mode == ConversionMode.HARDWARE

    @patch("subprocess.run")
    def test_is_available_when_present(self, mock_run: MagicMock) -> None:
        """Test is_available returns True when encoder is present."""
        mock_run.return_value = MagicMock(
            stdout="V..... hevc_videotoolbox    HEVC (Apple VideoToolbox)"
        )
        converter = HardwareConverter()
        assert converter.is_available() is True

    @patch("subprocess.run")
    def test_is_available_when_absent(self, mock_run: MagicMock) -> None:
        """Test is_available returns False when encoder is absent."""
        mock_run.return_value = MagicMock(stdout="V..... libx264    libx264 H.264")
        converter = HardwareConverter()
        assert converter.is_available() is False

    @patch("subprocess.run")
    def test_is_available_caches_result(self, mock_run: MagicMock) -> None:
        """Test is_available caches the result."""
        mock_run.return_value = MagicMock(
            stdout="V..... hevc_videotoolbox    HEVC"
        )
        converter = HardwareConverter()

        # Call multiple times
        converter.is_available()
        converter.is_available()
        converter.is_available()

        # Should only call subprocess once
        assert mock_run.call_count == 1

    def test_build_command(self) -> None:
        """Test FFmpeg command is built correctly."""
        converter = HardwareConverter()
        request = ConversionRequest(
            input_path=Path("/input/video.mov"),
            output_path=Path("/output/video.mp4"),
            quality=50,
            audio_mode="copy",
        )

        command = converter.build_command(request)

        assert "ffmpeg" in command
        assert "-i" in command
        assert "/input/video.mov" in command
        assert "-c:v" in command
        assert "hevc_videotoolbox" in command
        assert "-q:v" in command
        assert "50" in command
        assert "-tag:v" in command
        assert "hvc1" in command
        assert "-c:a" in command
        assert "copy" in command
        assert "/output/video.mp4" in command

    def test_build_command_clamps_quality(self) -> None:
        """Test quality is clamped to valid range."""
        converter = HardwareConverter()

        # Quality too high
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            quality=150,
        )
        command = converter.build_command(request)
        quality_idx = command.index("-q:v") + 1
        assert command[quality_idx] == "100"

        # Quality too low
        request.quality = -10
        command = converter.build_command(request)
        quality_idx = command.index("-q:v") + 1
        assert command[quality_idx] == "1"


class TestSoftwareConverter:
    """Tests for SoftwareConverter."""

    def test_encoder_name(self) -> None:
        """Test encoder name is correct."""
        converter = SoftwareConverter()
        assert converter.encoder_name == "libx265"

    def test_mode_is_software(self) -> None:
        """Test mode is SOFTWARE."""
        converter = SoftwareConverter()
        assert converter.mode == ConversionMode.SOFTWARE

    @patch("subprocess.run")
    def test_is_available_when_present(self, mock_run: MagicMock) -> None:
        """Test is_available returns True when encoder is present."""
        mock_run.return_value = MagicMock(
            stdout="V..... libx265    libx265 H.265 / HEVC"
        )
        converter = SoftwareConverter()
        assert converter.is_available() is True

    @patch("subprocess.run")
    def test_is_available_when_absent(self, mock_run: MagicMock) -> None:
        """Test is_available returns False when encoder is absent."""
        mock_run.return_value = MagicMock(stdout="V..... libx264    libx264")
        converter = SoftwareConverter()
        assert converter.is_available() is False

    def test_build_command(self) -> None:
        """Test FFmpeg command is built correctly."""
        converter = SoftwareConverter()
        request = ConversionRequest(
            input_path=Path("/input/video.mov"),
            output_path=Path("/output/video.mp4"),
            crf=20,
            preset="slow",
            audio_mode="aac",
        )

        command = converter.build_command(request)

        assert "ffmpeg" in command
        assert "-c:v" in command
        assert "libx265" in command
        assert "-crf" in command
        assert "20" in command
        assert "-preset" in command
        assert "slow" in command
        assert "-c:a" in command
        assert "aac" in command

    def test_build_command_clamps_crf(self) -> None:
        """Test CRF is clamped to valid range."""
        converter = SoftwareConverter()

        # CRF too high
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            crf=60,
        )
        command = converter.build_command(request)
        crf_idx = command.index("-crf") + 1
        assert command[crf_idx] == "51"

        # CRF too low
        request.crf = -5
        command = converter.build_command(request)
        crf_idx = command.index("-crf") + 1
        assert command[crf_idx] == "0"

    def test_build_command_validates_preset(self) -> None:
        """Test invalid preset is replaced with default."""
        converter = SoftwareConverter()
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            preset="invalid_preset",
        )
        command = converter.build_command(request)
        preset_idx = command.index("-preset") + 1
        assert command[preset_idx] == "medium"

    def test_valid_presets(self) -> None:
        """Test all valid presets are accepted."""
        converter = SoftwareConverter()
        valid_presets = [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
            "placebo",
        ]

        for preset in valid_presets:
            request = ConversionRequest(
                input_path=Path("input.mov"),
                output_path=Path("output.mp4"),
                preset=preset,
            )
            command = converter.build_command(request)
            preset_idx = command.index("-preset") + 1
            assert command[preset_idx] == preset

    def test_build_command_10bit_encoding(self) -> None:
        """Test 10-bit encoding adds correct pixel format."""
        converter = SoftwareConverter()
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            bit_depth=10,
        )
        command = converter.build_command(request)

        assert "-pix_fmt" in command
        pix_fmt_idx = command.index("-pix_fmt") + 1
        assert command[pix_fmt_idx] == "yuv420p10le"

    def test_build_command_10bit_with_hdr(self) -> None:
        """Test 10-bit HDR encoding adds x265-params."""
        converter = SoftwareConverter()
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            bit_depth=10,
            hdr=True,
        )
        command = converter.build_command(request)

        assert "-pix_fmt" in command
        assert "-x265-params" in command
        x265_idx = command.index("-x265-params") + 1
        assert "hdr-opt=1" in command[x265_idx]
        assert "colorprim=bt2020" in command[x265_idx]

    def test_build_command_8bit_no_hdr_params(self) -> None:
        """Test 8-bit encoding does not add 10-bit specific options."""
        converter = SoftwareConverter()
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            bit_depth=8,
        )
        command = converter.build_command(request)

        assert "-pix_fmt" not in command
        assert "-x265-params" not in command

    def test_build_command_hdr_requires_10bit(self) -> None:
        """Test HDR flag alone does not add x265-params without 10-bit."""
        converter = SoftwareConverter()
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            bit_depth=8,
            hdr=True,
        )
        command = converter.build_command(request)

        # HDR params should not be added for 8-bit content
        assert "-x265-params" not in command

    def test_build_command_invalid_bit_depth_defaults_to_8(self) -> None:
        """Test invalid bit depth falls back to 8-bit."""
        converter = SoftwareConverter()
        request = ConversionRequest(
            input_path=Path("input.mov"),
            output_path=Path("output.mp4"),
            bit_depth=12,  # Invalid, should default to 8
        )
        command = converter.build_command(request)

        # Should not have 10-bit options
        assert "-pix_fmt" not in command

    def test_valid_bit_depths(self) -> None:
        """Test valid bit depths constant is correct."""
        assert SoftwareConverter.VALID_BIT_DEPTHS == [8, 10]
        assert SoftwareConverter.DEFAULT_BIT_DEPTH == 8


class TestConverterFactory:
    """Tests for ConverterFactory."""

    @patch.object(HardwareConverter, "is_available", return_value=True)
    @patch.object(SoftwareConverter, "is_available", return_value=True)
    def test_get_hardware_converter(
        self, mock_sw: MagicMock, mock_hw: MagicMock
    ) -> None:
        """Test getting hardware converter."""
        factory = ConverterFactory()
        converter = factory.get_converter(ConversionMode.HARDWARE)
        assert isinstance(converter, HardwareConverter)

    @patch.object(HardwareConverter, "is_available", return_value=True)
    @patch.object(SoftwareConverter, "is_available", return_value=True)
    def test_get_software_converter(
        self, mock_sw: MagicMock, mock_hw: MagicMock
    ) -> None:
        """Test getting software converter."""
        factory = ConverterFactory()
        converter = factory.get_converter(ConversionMode.SOFTWARE)
        assert isinstance(converter, SoftwareConverter)

    @patch.object(HardwareConverter, "is_available", return_value=True)
    @patch.object(SoftwareConverter, "is_available", return_value=True)
    def test_auto_select_prefers_hardware(
        self, mock_sw: MagicMock, mock_hw: MagicMock
    ) -> None:
        """Test auto-selection prefers hardware."""
        factory = ConverterFactory()
        converter = factory.get_converter()
        assert isinstance(converter, HardwareConverter)

    @patch.object(HardwareConverter, "is_available", return_value=False)
    @patch.object(SoftwareConverter, "is_available", return_value=True)
    def test_auto_select_falls_back_to_software(
        self, mock_sw: MagicMock, mock_hw: MagicMock
    ) -> None:
        """Test auto-selection falls back to software."""
        factory = ConverterFactory()
        converter = factory.get_converter()
        assert isinstance(converter, SoftwareConverter)

    @patch.object(HardwareConverter, "is_available", return_value=False)
    @patch.object(SoftwareConverter, "is_available", return_value=True)
    def test_hardware_fallback_to_software(
        self, mock_sw: MagicMock, mock_hw: MagicMock
    ) -> None:
        """Test hardware mode falls back to software when unavailable."""
        factory = ConverterFactory()
        converter = factory.get_converter(ConversionMode.HARDWARE, fallback=True)
        assert isinstance(converter, SoftwareConverter)

    @patch.object(HardwareConverter, "is_available", return_value=False)
    @patch.object(SoftwareConverter, "is_available", return_value=True)
    def test_hardware_no_fallback_raises(
        self, mock_sw: MagicMock, mock_hw: MagicMock
    ) -> None:
        """Test hardware mode raises when unavailable and no fallback."""
        factory = ConverterFactory()
        with pytest.raises(EncoderNotAvailableError):
            factory.get_converter(ConversionMode.HARDWARE, fallback=False)

    @patch.object(HardwareConverter, "is_available", return_value=False)
    @patch.object(SoftwareConverter, "is_available", return_value=False)
    def test_no_encoder_available_raises(
        self, mock_sw: MagicMock, mock_hw: MagicMock
    ) -> None:
        """Test exception when no encoder is available."""
        factory = ConverterFactory()
        with pytest.raises(EncoderNotAvailableError):
            factory.get_converter()

    @patch.object(HardwareConverter, "is_available", return_value=True)
    @patch.object(SoftwareConverter, "is_available", return_value=True)
    def test_get_available_converters(
        self, mock_sw: MagicMock, mock_hw: MagicMock
    ) -> None:
        """Test getting list of available converters."""
        factory = ConverterFactory()
        available = factory.get_available_converters()
        assert len(available) == 2
        assert any(isinstance(c, HardwareConverter) for c in available)
        assert any(isinstance(c, SoftwareConverter) for c in available)

    @patch.object(HardwareConverter, "is_available", return_value=True)
    @patch.object(SoftwareConverter, "is_available", return_value=False)
    def test_get_available_converters_partial(
        self, mock_sw: MagicMock, mock_hw: MagicMock
    ) -> None:
        """Test getting available converters when only hardware is available."""
        factory = ConverterFactory()
        available = factory.get_available_converters()
        assert len(available) == 1
        assert isinstance(available[0], HardwareConverter)


class TestModuleLevelGetConverter:
    """Tests for module-level get_converter function."""

    @patch.object(HardwareConverter, "is_available", return_value=True)
    @patch.object(SoftwareConverter, "is_available", return_value=True)
    def test_get_converter_function(
        self, mock_sw: MagicMock, mock_hw: MagicMock
    ) -> None:
        """Test module-level get_converter function."""
        # Reset the module-level factory
        import video_converter.converters.factory as factory_module

        factory_module._default_factory = None

        converter = get_converter()
        assert converter is not None
