# H.264→H.265 Auto Conversion System Architecture Overview

## System Goals

Automatically convert H.264 videos stored in macOS Photos to H.265 (HEVC) to:

1. **Save Storage Space**: 50%+ file size reduction
2. **Maintain Quality**: Visually lossless conversion
3. **Preserve Metadata**: Maintain GPS, dates, album info
4. **Full Automation**: Minimize user intervention

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    macOS Photos Library                          │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐        │
│  │ H.264 Videos  │  │   Metadata    │  │    Albums     │        │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘        │
└──────────┼──────────────────┼──────────────────┼────────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Video Extractor                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  osxphotos / PhotoKit                                     │  │
│  │  - Detect H.264 videos                                    │  │
│  │  - Export original files                                  │  │
│  │  - Extract metadata                                       │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Video Converter Engine                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  FFmpeg + VideoToolbox                                    │  │
│  │  - hevc_videotoolbox (hardware acceleration)              │  │
│  │  - CRF/Quality settings                                   │  │
│  │  - Metadata mapping                                       │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Post-Processing                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ExifTool / Metadata Restoration                          │  │
│  │  - Restore GPS information                                │  │
│  │  - Restore creation date                                  │  │
│  │  - Sync file timestamps                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Output Management                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  H.265 Videos   │  │   Backup Dir    │  │   Logs/Reports  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Video Extractor

**Role**: Identify and extract target videos from Photos library

**Technology Stack**:
- **osxphotos** (recommended): Python-based, provides CLI and API
- **PhotoKit**: Swift native, for app development

**Key Functions**:
```python
# osxphotos example
import osxphotos

def get_h264_videos(photosdb):
    """Filter only H.264 codec videos"""
    videos = []
    for photo in photosdb.photos():
        if photo.ismovie and photo.path:
            # Codec check logic
            if is_h264(photo.path):
                videos.append(photo)
    return videos
```

### 2. Codec Detector

**Role**: Verify current codec of video

**Implementation**:
```bash
#!/bin/bash
# Check codec with FFprobe
get_video_codec() {
    ffprobe -v error \
        -select_streams v:0 \
        -show_entries stream=codec_name \
        -of default=noprint_wrappers=1:nokey=1 \
        "$1"
}

# Usage example
codec=$(get_video_codec "video.mp4")
if [ "$codec" = "h264" ]; then
    echo "Conversion target"
fi
```

### 3. Video Converter Engine

**Role**: Perform H.264 → H.265 conversion

**Two Modes**:

| Mode | Encoder | Speed | Quality | Recommended For |
|------|---------|-------|---------|-----------------|
| Fast Mode | hevc_videotoolbox | Very fast | Good | Batch conversion |
| High Quality Mode | libx265 | Slow | Best | Important videos |

**Core Settings**:
```bash
# Fast mode (hardware)
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -q:v 45 \
  -tag:v hvc1 \
  -c:a copy \
  -map_metadata 0 \
  output.mp4

# High quality mode (software)
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 20 \
  -preset slow \
  -c:a copy \
  -map_metadata 0 \
  output.mp4
```

### 4. Metadata Manager

**Role**: Preserve GPS, dates, and other metadata

**Processing Flow**:
```
Original Video → Extract Metadata → Convert → Restore Metadata → Sync Timestamps
```

**Implementation**:
```bash
# Metadata restoration
restore_metadata() {
    original="$1"
    converted="$2"

    # FFmpeg metadata (basic)
    # Handled with -map_metadata 0 option

    # Restore additional metadata with ExifTool
    exiftool -tagsFromFile "$original" \
        -all:all \
        -overwrite_original \
        "$converted"

    # Sync file timestamps
    touch -r "$original" "$converted"
}
```

### 5. Automation Controller

**Role**: Automate entire conversion process

**Implementation Options**:

| Method | Trigger | Recommended Scenario |
|--------|---------|---------------------|
| launchd + WatchPaths | Folder change detection | Real-time processing |
| launchd + StartCalendarInterval | Scheduled time | Batch processing |
| Folder Actions | File addition | Simple automation |

## Directory Structure

```
~/Videos/VideoConverter/
├── input/              # Videos awaiting conversion
├── output/             # Converted videos
├── processed/          # Processed original backups
├── failed/             # Failed conversions
├── logs/               # Conversion logs
│   ├── conversion.log
│   └── errors.log
└── config/             # Configuration files
    └── settings.json
```

## Configuration File Structure

```json
{
  "version": "0.1.0.0",
  "encoding": {
    "mode": "hardware",
    "quality": 45,
    "preset": "slow",
    "crf": 22
  },
  "paths": {
    "input": "~/Videos/VideoConverter/input",
    "output": "~/Videos/VideoConverter/output",
    "processed": "~/Videos/VideoConverter/processed",
    "failed": "~/Videos/VideoConverter/failed"
  },
  "automation": {
    "method": "launchd",
    "schedule": "daily",
    "time": "03:00"
  },
  "photos": {
    "autoExport": true,
    "skipEdited": true,
    "downloadFromICloud": true
  },
  "notification": {
    "enabled": true,
    "onComplete": true,
    "onError": true
  }
}
```

## Workflow

### Complete Processing Flow

```
1. Trigger Occurred
   ├─ Manual execution
   ├─ Scheduled time reached
   └─ Folder change detected

2. Photos Library Scan
   ├─ Query all video list
   ├─ Filter H.264 codec
   └─ Exclude already converted items

3. Video Export
   ├─ Copy original file
   ├─ Extract metadata
   └─ Download from iCloud (if needed)

4. Conversion Execution
   ├─ Run FFmpeg
   ├─ Monitor progress
   └─ Error handling

5. Post-processing
   ├─ Restore metadata
   ├─ Sync timestamps
   └─ Quality validation (optional)

6. Cleanup
   ├─ Backup/delete original
   ├─ Log recording
   └─ Send notification
```

### Error Handling Strategy

```python
class ConversionError(Exception):
    pass

def convert_with_retry(input_path, output_path, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = run_ffmpeg(input_path, output_path)
            if validate_output(output_path):
                return True
        except Exception as e:
            log_error(f"Attempt {attempt + 1} failed: {e}")

            if attempt == max_retries - 1:
                move_to_failed(input_path)
                raise ConversionError(f"Failed after {max_retries} attempts")

            time.sleep(5 * (attempt + 1))  # Exponential backoff

    return False
```

## Performance Optimization

### Parallel Processing

```bash
# Using GNU Parallel
find "$INPUT_DIR" -name "*.mp4" | \
    parallel -j 2 ~/Scripts/convert_single.sh {}
```

### Resource Management

```python
import os
import multiprocessing

def get_optimal_workers():
    """Optimal worker count based on system resources"""
    cpu_count = multiprocessing.cpu_count()

    # Hardware encoding: Low CPU impact
    if use_hardware_encoding:
        return min(3, cpu_count)

    # Software encoding: CPU intensive
    return max(1, cpu_count // 4)
```

## Monitoring and Logging

### Log Format

```
[2024-12-21 03:00:00] INFO  Starting batch conversion
[2024-12-21 03:00:01] INFO  Found 15 videos to convert
[2024-12-21 03:00:05] INFO  Converting: vacation_2024.mov (1/15)
[2024-12-21 03:02:30] INFO  Completed: vacation_2024.mov (2.5 GB → 1.1 GB)
[2024-12-21 03:02:31] ERROR Failed: corrupted_video.mp4 - Invalid data found
[2024-12-21 03:45:00] INFO  Batch completed: 14 success, 1 failed
```

### Statistics Report

```json
{
  "date": "2024-12-21",
  "totalVideos": 15,
  "successful": 14,
  "failed": 1,
  "originalSize": "35.2 GB",
  "convertedSize": "15.8 GB",
  "savedSpace": "19.4 GB (55%)",
  "totalDuration": "45m 32s",
  "averageSpeed": "3.2x realtime"
}
```

## Technical Requirements

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| macOS | 10.15+ | Operating System |
| Python | 3.10+ | Run osxphotos |
| FFmpeg | 5.0+ | Video conversion |
| ExifTool | 12.0+ | Metadata processing |
| osxphotos | 0.70+ | Photos access |

### Installation Commands

```bash
# Homebrew packages
brew install ffmpeg exiftool python@3.12

# Python packages
pip install osxphotos
```

### Recommended Hardware Specifications

| Item | Minimum | Recommended |
|------|---------|-------------|
| CPU | M1 | M2 Pro / M3 |
| RAM | 8GB | 16GB+ |
| Storage | 2x conversion target | 3x conversion target |

## Next Steps

When implementing based on this architecture, the following order is recommended:

1. **Environment Setup**: Install required software and configure permissions
2. **Core Script Development**: Conversion engine and metadata processing
3. **Automation Setup**: Configure launchd or preferred method
4. **Testing**: Validate with small videos
5. **Add Monitoring**: Logging and notification system
6. **Gradual Deployment**: Expand to entire library

## References

- [01-codec-comparison.md](01-codec-comparison.md) - Codec comparison
- [02-ffmpeg-hevc-encoding.md](02-ffmpeg-hevc-encoding.md) - FFmpeg encoding guide
- [03-videotoolbox-hardware-acceleration.md](03-videotoolbox-hardware-acceleration.md) - Hardware acceleration
- [04-macos-photos-access.md](04-macos-photos-access.md) - Photos access methods
- [05-macos-automation-methods.md](05-macos-automation-methods.md) - Automation methods
