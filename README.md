# Video Converter

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![macOS](https://img.shields.io/badge/macOS-12.0+-000000.svg)](https://apple.com/macos)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Keep your precious memories, halve your storage**

Automated video codec conversion solution for macOS that converts H.264 videos to H.265 (HEVC), achieving **50%+ storage savings** while maintaining **visually identical quality** and **preserving all metadata**.

## Features

- **Automation**: Set once, runs daily automatically via launchd
- **Lossless Quality**: VMAF 93+ (visually indistinguishable)
- **Metadata Safe**: 100% preservation of GPS, dates, album info
- **Hardware Accelerated**: Fast conversion with Apple Silicon VideoToolbox
- **Photos Integration**: Direct access to macOS Photos library

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| macOS | 12.0 (Monterey) | 14.0+ (Sonoma) |
| CPU | Apple M1 | Apple M2 Pro+ |
| RAM | 8GB | 16GB+ |
| Python | 3.10+ | 3.12+ |

## Installation

```bash
# Clone the repository
git clone https://github.com/kcenon/video_converter.git
cd video_converter

# Install dependencies
brew install ffmpeg exiftool
pip install -e .

# Grant Photos access (will prompt on first run)
video-converter setup
```

## Quick Start

### Single File Conversion

```bash
video-converter convert input.mp4 output.mp4 --mode hardware
```

### Batch Conversion (Photos Library)

```bash
video-converter run --mode photos
```

### Batch Conversion with Priority

```bash
# Process smallest files first
video-converter run --priority size_smallest

# Process oldest files first
video-converter run --priority date_oldest

# Available priorities: fifo, date_oldest, date_newest, size_smallest, size_largest
```

### Resume Interrupted Conversion

If a conversion is interrupted (system crash, restart, or manual pause), you can resume from where it left off:

```bash
# Check for resumable sessions
video-converter status --sessions

# Resume the interrupted session
video-converter run --resume
```

Session state is automatically saved to `~/.local/share/video_converter/sessions/`.

### Enable Daily Automation

```bash
video-converter install-service --time 03:00
```

## Usage

```bash
video-converter <command> [options]

Commands:
  convert       Single file conversion
  run           Batch conversion execution
  status        Service status check
  stats         Conversion statistics
  config        Configuration management
  install       Install automation service
  uninstall     Remove automation service

Global Options:
  --config      Config file path
  --verbose     Detailed log output
  --quiet       Minimal output
  --help        Show help
```

## Configuration

Configuration file location: `~/.config/video_converter/config.json`

```json
{
  "version": "1.0.0",
  "encoding": {
    "mode": "hardware",
    "quality": 45,
    "crf": 22,
    "preset": "medium"
  },
  "paths": {
    "output": "~/Videos/Converted",
    "processed": "~/Videos/Processed",
    "failed": "~/Videos/Failed"
  },
  "automation": {
    "enabled": false,
    "schedule": "daily",
    "time": "03:00"
  },
  "photos": {
    "include_albums": [],
    "exclude_albums": ["Screenshots"],
    "download_from_icloud": true
  },
  "processing": {
    "max_concurrent": 2,
    "validate_quality": true,
    "preserve_original": true
  },
  "notification": {
    "on_complete": true,
    "on_error": true,
    "daily_summary": false
  }
}
```

### Environment Variable Overrides

Configuration can be overridden using environment variables with the `VIDEO_CONVERTER_` prefix:

```bash
# Override encoding mode
export VIDEO_CONVERTER_ENCODING__MODE=software

# Override quality setting
export VIDEO_CONVERTER_ENCODING__QUALITY=80

# Override max concurrent jobs
export VIDEO_CONVERTER_PROCESSING__MAX_CONCURRENT=4
```

Note: Use double underscore (`__`) for nested configuration keys.

## How It Works

```
Photos Library ──▶ H.264 Detection ──▶ VideoToolbox ──▶ H.265 Output
                                           │
                                           ▼
                              Metadata Preservation (ExifTool)
                                           │
                                           ▼
                              Quality Validation (FFprobe)
```

1. **Scan**: Query H.264 videos from Photos library using osxphotos
2. **Convert**: Hardware-accelerated conversion via VideoToolbox
3. **Preserve**: Copy all metadata including GPS coordinates
4. **Validate**: Verify integrity and quality of converted files
5. **Report**: Send macOS notification with summary

## Documentation

| Document | Description |
|----------|-------------|
| [PRD](docs/PRD.md) | Product Requirements Document |
| [SRS](docs/SRS.md) | Software Requirements Specification |
| [SDS](docs/SDS.md) | Software Design Specification |
| [Architecture](docs/architecture/) | System architecture and diagrams |
| [Development Plan](docs/development-plan.md) | Development phases and timeline |

## Technology Stack

- **Python 3.10+**: Core application
- **FFmpeg + VideoToolbox**: Video encoding (hardware accelerated)
- **osxphotos**: macOS Photos library access
- **ExifTool**: Metadata extraction and preservation
- **launchd**: macOS native automation

## Performance

| Video | Mode | Time | Compression |
|-------|------|------|-------------|
| 4K 30min | Hardware | ~5 min | 50-60% |
| 1080p 10min | Hardware | ~30 sec | 50-60% |
| 4K 30min | Software | ~30 min | 55-65% |

## Roadmap

- [x] v1.0.0 - CLI with automation (Current)
- [ ] v1.1.0 - GUI application
- [ ] v1.2.0 - VMAF quality verification
- [ ] v2.0.0 - AV1 codec support

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) before submitting a PR.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [FFmpeg](https://ffmpeg.org/) - Video processing
- [osxphotos](https://github.com/RhetTbull/osxphotos) - Photos library access
- [ExifTool](https://exiftool.org/) - Metadata handling
