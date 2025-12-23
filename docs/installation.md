# Installation

Complete installation guide for Video Converter.

## System Requirements

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Apple M1 | Apple M2 Pro or better |
| RAM | 8GB | 16GB+ |
| Storage | 2x conversion target | 3x conversion target |

### Software

| Software | Version | Installation |
|----------|---------|--------------|
| macOS | 12.0+ (Monterey) | - |
| Python | 3.10+ | `brew install python@3.12` |
| FFmpeg | 5.0+ | `brew install ffmpeg` |
| ExifTool | 12.0+ | `brew install exiftool` |

## Installation Methods

### Using pip (Recommended)

```bash
pip install video-converter
```

### From Source

```bash
git clone https://github.com/kcenon/video_converter.git
cd video_converter
pip install -e .
```

### With Development Dependencies

```bash
pip install -e ".[dev]"
```

### With GUI Support

```bash
pip install -e ".[gui]"
```

### With Documentation Dependencies

```bash
pip install -e ".[docs]"
```

## Verify Installation

```bash
# Check CLI
video-converter --version

# Check dependencies
video-converter check-deps
```

**Expected output:**
```
video-converter 0.2.0.0

Checking dependencies...
✅ Python 3.12.0
✅ FFmpeg 6.1.1
✅ ExifTool 12.76
✅ osxphotos 0.70.1
All dependencies satisfied!
```

## Troubleshooting

### FFmpeg Not Found

```bash
# Install via Homebrew
brew install ffmpeg

# Verify installation
ffmpeg -version
```

### ExifTool Not Found

```bash
# Install via Homebrew
brew install exiftool

# Verify installation
exiftool -ver
```

### Permission Issues

For Photos library access:

1. Open **System Preferences** > **Privacy & Security** > **Photos**
2. Add **Terminal** (or your terminal app) to the allowed list
3. Restart your terminal

### Python Version Issues

```bash
# Install Python 3.12
brew install python@3.12

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install video-converter
pip install video-converter
```
