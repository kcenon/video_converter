# FFmpeg H.265/HEVC Encoding Guide

## Overview

This document covers video conversion methods from H.264 to H.265 (HEVC) using FFmpeg and optimal settings.

## Basic Commands

### Simplest Conversion

```bash
ffmpeg -i input.mp4 -c:v libx265 -crf 28 -c:a copy output.mp4
```

### Recommended Conversion (Quality Priority)

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 23 \
  -preset slow \
  -profile:v main \
  -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -map_metadata 0 \
  -movflags use_metadata_tags \
  output.mp4
```

## CRF (Constant Rate Factor) Settings

### CRF Range

| CRF Value | Quality | Use Case |
|-----------|---------|----------|
| 0 | Lossless | Archiving (very large file size) |
| 18-20 | Visually lossless | High quality archiving |
| 23 | Default | General use |
| 28 | Good | File size savings |
| 35+ | Low quality | Not recommended |

### H.264 ↔ H.265 CRF Conversion Formula

> H.265 CRF ≈ H.264 CRF + 4~6
>
> Example: H.264 CRF 23 ≈ H.265 CRF 27-29

```bash
# To maintain H.264 quality, lower CRF by 4-6 for H.265
# Example: H.265 quality equivalent to H.264 CRF 23
ffmpeg -i input_h264.mp4 -c:v libx265 -crf 19 output.mp4
```

## Preset Options

### Speed vs Quality Trade-off

| Preset | Speed | File Size | Recommended Use |
|--------|-------|-----------|-----------------|
| ultrafast | Fastest | Largest | Testing |
| superfast | Very fast | Very large | Quick conversion needed |
| veryfast | Fast | Large | Real-time encoding |
| faster | Fast | Large | Fast batch work |
| fast | Medium | Medium | General use |
| medium | Medium | Medium | Default |
| slow | Slow | Small | **Recommended** |
| slower | Very slow | Very small | Final output |
| veryslow | Slowest | Smallest | Maximum compression needed |

```bash
# Recommended: slow preset for good quality/size ratio
ffmpeg -i input.mp4 -c:v libx265 -crf 23 -preset slow output.mp4
```

## Metadata Preservation

### Basic Metadata Copy

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 -crf 23 \
  -c:a copy \
  -map_metadata 0 \
  output.mp4
```

### Full Metadata Preservation (Including GPS)

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 -crf 23 \
  -c:a copy \
  -map 0 \
  -map_metadata 0 \
  -movflags use_metadata_tags \
  output.mp4
```

### Complete Metadata Restoration Using ExifTool

```bash
# 1. First convert with FFmpeg
ffmpeg -i original.mp4 -c:v libx265 -crf 23 converted.mp4

# 2. Copy metadata with ExifTool
exiftool -tagsFromFile original.mp4 converted.mp4

# 3. Restore file timestamps
touch -r original.mp4 converted.mp4
```

## Audio Processing

### Audio Stream Copy (Recommended)

```bash
ffmpeg -i input.mp4 -c:v libx265 -crf 23 -c:a copy output.mp4
```

### Audio Re-encoding (When Needed)

```bash
# AAC encoding
ffmpeg -i input.mp4 \
  -c:v libx265 -crf 23 \
  -c:a aac -b:a 192k \
  output.mp4

# Maintain original audio quality (requires libfdk_aac)
ffmpeg -i input.mp4 \
  -c:v libx265 -crf 23 \
  -c:a libfdk_aac -vbr 5 \
  output.mp4
```

## Advanced Settings

### VMAF 95 Achievement Settings (2025 Benchmark)

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -preset slow \
  -crf 20.6 \
  -g 600 \
  -keyint_min 600 \
  -tune fastdecode \
  -c:a copy \
  -map_metadata 0 \
  output.mp4
```

### 10-bit Encoding (HDR Compatible)

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 22 \
  -preset slow \
  -profile:v main10 \
  -pix_fmt yuv420p10le \
  output.mp4
```

### 2-Pass Encoding (Fixed Bitrate)

```bash
# Pass 1
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -b:v 5M \
  -preset slow \
  -pass 1 \
  -an \
  -f null /dev/null

# Pass 2
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -b:v 5M \
  -preset slow \
  -pass 2 \
  -c:a copy \
  output.mp4
```

## Batch Conversion Scripts

### Convert All MP4s in a Single Folder

```bash
#!/bin/bash
INPUT_DIR="./input"
OUTPUT_DIR="./output"
CRF=23

mkdir -p "$OUTPUT_DIR"

for file in "$INPUT_DIR"/*.mp4; do
    filename=$(basename "$file" .mp4)
    echo "Converting: $file"

    ffmpeg -i "$file" \
        -c:v libx265 \
        -crf $CRF \
        -preset slow \
        -c:a copy \
        -map_metadata 0 \
        -movflags use_metadata_tags \
        "$OUTPUT_DIR/${filename}_hevc.mp4"

    # Restore metadata
    exiftool -tagsFromFile "$file" "$OUTPUT_DIR/${filename}_hevc.mp4" 2>/dev/null
    touch -r "$file" "$OUTPUT_DIR/${filename}_hevc.mp4"
done
```

### With Progress Display

```bash
#!/bin/bash
# Use pv or ffmpeg's -progress option for progress display

ffmpeg -i input.mp4 \
  -c:v libx265 -crf 23 -preset slow \
  -c:a copy \
  -progress pipe:1 \
  output.mp4 2>&1 | \
  while read line; do
    if [[ "$line" == *"out_time="* ]]; then
      echo "Progress: ${line#*=}"
    fi
  done
```

## Encoding Quality Verification

### VMAF Score Calculation

```bash
ffmpeg -i converted.mp4 -i original.mp4 \
  -lavfi libvmaf="model=version=vmaf_v0.6.1" \
  -f null -
```

### PSNR/SSIM Calculation

```bash
# PSNR
ffmpeg -i converted.mp4 -i original.mp4 \
  -lavfi psnr="stats_file=psnr.log" \
  -f null -

# SSIM
ffmpeg -i converted.mp4 -i original.mp4 \
  -lavfi ssim="stats_file=ssim.log" \
  -f null -
```

## Troubleshooting

### QuickTime Compatibility Issues

```bash
# Add QuickTime compatible settings
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 23 \
  -tag:v hvc1 \
  -c:a aac \
  output.mp4
```

### Preserve Color Space

```bash
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 23 \
  -color_primaries bt709 \
  -color_trc bt709 \
  -colorspace bt709 \
  output.mp4
```

## Installing FFmpeg on macOS

```bash
# Using Homebrew
brew install ffmpeg

# Install with all codecs
brew install ffmpeg --with-libvpx --with-libvorbis
```

## References

- [OTTVerse - HEVC Encoding Guide](https://ottverse.com/hevc-encoding-using-ffmpeg-crf-cbr-2-pass-lossless/)
- [scottstuff.net - 2025 H.265 Benchmarks](https://scottstuff.net/posts/2025/03/17/benchmarking-ffmpeg-h265/)
- [slhck.info - CRF Guide](https://slhck.info/video/2017/02/24/crf-guide.html)
- [Mux - Video Compression Guide](https://www.mux.com/articles/how-to-compress-video-files-while-maintaining-quality-with-ffmpeg)
- [FFmpeg Documentation](https://www.ffmpeg.org/ffmpeg.html)
