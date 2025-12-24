# Quick Start Guide

Get started with Video Converter in 5 minutes.

## Prerequisites

Ensure you have the following installed:

```bash
# Check Python version (3.10+ required)
python3 --version

# Install FFmpeg
brew install ffmpeg

# Install ExifTool
brew install exiftool
```

## Installation

```bash
# Clone repository
git clone https://github.com/kcenon/video_converter.git
cd video_converter

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install
pip install -e .
```

## Basic Usage

### Convert a Single File

```bash
video-converter convert input.mp4 output.mp4
```

**Output:**
```
Converting: input.mp4
[████████████████████] 100% | 1.5GB → 680MB | Speed: 6.2x
✅ Complete: Saved 820MB (54%)
```

### Preview Photos Library (Dry Run)

```bash
video-converter run --source photos --dry-run
```

**Output:**
```
Scanning Photos library...

Found 89 H.264 videos to convert.
Total size: 45.2 GB
Estimated savings: ~22.6 GB (50%)

Dry run complete. Use 'video-converter run --source photos' to start conversion.
```

### Batch Convert Photos Library

```bash
video-converter run --source photos
```

## Hardware vs Software Encoding

| Mode | Command | Speed | Quality | Use Case |
|------|---------|-------|---------|----------|
| Hardware | `--mode hardware` | 6-20x realtime | Good | Daily use, batch conversion |
| Software | `--mode software` | 0.5-2x realtime | Excellent | Archival, maximum quality |

```bash
# Hardware encoding (default)
video-converter convert input.mp4 output.mp4 --mode hardware

# Software encoding (higher quality)
video-converter convert input.mp4 output.mp4 --mode software --quality 85
```

## Quality Settings

The `--quality` option works for both hardware and software encoding (1-100, higher = better quality):

```bash
# Default quality
video-converter convert input.mp4 output.mp4

# Higher quality (larger file)
video-converter convert input.mp4 output.mp4 --quality 85

# Lower quality (smaller file)
video-converter convert input.mp4 output.mp4 --quality 50
```

### Software Encoding with Quality

```bash
# Software encoding with high quality
video-converter convert input.mp4 output.mp4 --mode software --quality 90

# Software encoding with medium quality
video-converter convert input.mp4 output.mp4 --mode software --quality 70
```

## Next Steps

- [CLI Usage Guide](guides/cli-usage.md) - Complete command reference
- [Photos Workflow](guides/photos-workflow.md) - Work with Photos library
- [Automation](guides/automation.md) - Set up scheduled conversions
- [Examples](examples/basic.md) - More usage examples
