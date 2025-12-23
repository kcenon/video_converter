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

## Advanced Usage

### Photos Library Re-Import

Convert videos from Photos and import converted versions back:

```bash
# Re-import converted videos to Photos (archive originals)
video-converter run --source photos --reimport

# Re-import and delete originals (requires confirmation)
video-converter run --source photos --reimport --delete-originals --confirm-delete

# Re-import and keep both original and converted
video-converter run --source photos --reimport --keep-originals
```

### Concurrent Processing

Speed up batch conversions with parallel processing:

```bash
# Set max concurrent conversions
video-converter config-set processing.max_concurrent 4

# Run batch conversion (uses configured concurrency)
video-converter run --source photos

# Or use environment variable
export VIDEO_CONVERTER_PROCESSING__MAX_CONCURRENT=4
video-converter run --input-dir ~/Videos
```

### VMAF Quality Validation

Ensure converted videos meet quality thresholds:

```bash
# Enable VMAF measurement during conversion
video-converter convert input.mp4 --vmaf

# Set custom VMAF threshold (default: 93)
video-converter convert input.mp4 --vmaf --vmaf-threshold 85

# Enable VMAF globally
video-converter config-set processing.enable_vmaf true
```

### Service Management

Control the automation service:

```bash
# Check current status with next run time
video-converter status

# Manually start/stop the service
video-converter service-start
video-converter service-stop

# View service logs
video-converter service-logs

# Follow logs in real-time
video-converter service-logs -f

# View error logs
video-converter service-logs --stderr
```

### iCloud File Handling

Handle videos stored in iCloud:

```bash
# Auto-download iCloud files during conversion (default: enabled)
video-converter config-set folder.auto_download_icloud true

# Set download timeout (seconds)
video-converter config-set folder.icloud_timeout 3600

# Skip cloud-only files on timeout
video-converter config-set folder.skip_icloud_on_timeout true
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
