# Quick Start Guide

Get started with Video Converter in 5 minutes.

## Prerequisites

- **macOS 12.0+** (Monterey or later)
- **Python 3.10+**
- **Homebrew** (for dependency installation)

## Installation

### Step 1: Install Dependencies

```bash
brew install ffmpeg exiftool
```

### Step 2: Clone and Install

```bash
git clone https://github.com/kcenon/video_converter.git
cd video_converter
pip install -e .
```

### Step 3: Verify Installation

```bash
video-converter --version
```

## Basic Usage

### Convert a Single Video

```bash
# Simple conversion (auto-generates output name)
video-converter convert vacation.mp4

# Specify output file
video-converter convert vacation.mp4 vacation_h265.mp4
```

### Convert All Videos in a Folder

```bash
# Convert all H.264 videos in a directory
video-converter run --input-dir ~/Videos

# Include subdirectories
video-converter run --input-dir ~/Videos -r

# Preview what will be converted (dry run)
video-converter run --input-dir ~/Videos --dry-run
```

### Check Progress

During conversion, you'll see a progress bar:

```
Converting: vacation.mp4
Mode: hardware (hevc_videotoolbox)

⠋ Converting vacation.mp4 ━━━━━━━━━━━━━━━━━━━━ 30% │ 450 MB │ ETA: 2m 15s
```

## Enable Automation

Run conversions automatically every day:

```bash
# Install daily automation (runs at 3:00 AM)
video-converter install-service

# Check service status
video-converter status
```

## Common Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Show detailed output |
| `-q, --quiet` | Minimal output (errors only) |
| `--mode hardware` | Use hardware acceleration (default) |
| `--mode software` | Use software encoding |
| `--quality 80` | Set quality (1-100) |
| `-f, --force` | Overwrite existing files |

## View Statistics

```bash
# Show conversion statistics
video-converter stats

# Show detailed stats with recent conversions
video-converter stats --detailed
```

## Getting Help

```bash
# List all commands
video-converter --help

# Get help for a specific command
video-converter convert --help
```

## Next Steps

- Read the full [README.md](README.md) for advanced features
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if you encounter issues
- View [CHANGELOG.md](CHANGELOG.md) for version history
