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

### From Source (Recommended)

```bash
# Clone repository
git clone https://github.com/kcenon/video_converter.git
cd video_converter

# Create and activate virtual environment (Python 3.12 recommended)
python3.12 -m venv .venv
source .venv/bin/activate

# Install
pip3 install -e .
```

!!! warning "Python Version"
    Use **Python 3.10-3.12**. Python 3.13+ is not yet fully supported due to
    `pyobjc` compatibility. Check with: `python3.12 --version`

!!! note "Virtual Environment Required"
    Modern macOS requires using a virtual environment for Python packages.
    Always activate the virtual environment before using video-converter:
    `source .venv/bin/activate`

### With Development Dependencies

```bash
source .venv/bin/activate
pip3 install -e ".[dev]"
```

### With GUI Support

```bash
source .venv/bin/activate
pip3 install -e ".[gui]"
```

### With Documentation Dependencies

```bash
source .venv/bin/activate
pip3 install -e ".[docs]"
```

## Verify Installation

```bash
# Check CLI
video-converter --version

# Check FFmpeg
ffmpeg -version

# Check ExifTool
exiftool -ver
```

**Expected output:**
```
video-converter 0.2.0

ffmpeg version 6.1.1 ...
12.76
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

# Install video-converter from source
git clone https://github.com/kcenon/video_converter.git
cd video_converter
pip3 install -e .
```
