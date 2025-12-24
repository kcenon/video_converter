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
# Clone and install from source
git clone https://github.com/kcenon/video_converter.git
cd video_converter
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

### Scan Photos Library

```bash
video-converter scan --mode photos
```

**Output:**
```
Scanning Photos library...

╭─────────────────────────────────────────────╮
│         Photos Library Summary              │
├─────────────────────────────────────────────┤
│  Total videos:     156                      │
│  H.264 videos:     89                       │
│  Already HEVC:     67                       │
│  Total size:       45.2 GB                  │
│  Estimated savings: ~22.6 GB                │
╰─────────────────────────────────────────────╯
```

### Batch Convert Photos Library

```bash
video-converter run --mode photos
```

## Hardware vs Software Encoding

| Mode | Command | Speed | Quality | Use Case |
|------|---------|-------|---------|----------|
| Hardware | `--encoder hardware` | 6-20x realtime | Good | Daily use, batch conversion |
| Software | `--encoder software` | 0.5-2x realtime | Excellent | Archival, maximum quality |

```bash
# Hardware encoding (default)
video-converter convert input.mp4 output.mp4 --encoder hardware

# Software encoding (higher quality)
video-converter convert input.mp4 output.mp4 --encoder software --crf 20
```

## Quality Settings

### Hardware Encoder Quality

```bash
# Default quality (45)
video-converter convert input.mp4 output.mp4

# Higher quality (lower number = better quality, more space)
video-converter convert input.mp4 output.mp4 --quality 30

# Lower quality (higher number = smaller file)
video-converter convert input.mp4 output.mp4 --quality 60
```

### Software Encoder CRF

```bash
# Default CRF (22)
video-converter convert input.mp4 output.mp4 --encoder software

# Higher quality (lower CRF)
video-converter convert input.mp4 output.mp4 --encoder software --crf 18

# Smaller file (higher CRF)
video-converter convert input.mp4 output.mp4 --encoder software --crf 26
```

## Next Steps

- [CLI Usage Guide](guides/cli-usage.md) - Complete command reference
- [Photos Workflow](guides/photos-workflow.md) - Work with Photos library
- [Automation](guides/automation.md) - Set up scheduled conversions
- [Examples](examples/basic.md) - More usage examples
