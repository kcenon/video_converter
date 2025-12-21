# Apple Silicon VideoToolbox Hardware Acceleration Guide

## Overview

This document covers hardware-accelerated HEVC encoding methods using VideoToolbox on Apple Silicon (M1, M2, M3, M4) Macs.

## What is VideoToolbox?

VideoToolbox is Apple's low-level video encoding/decoding framework:

- Provides hardware-accelerated video processing on macOS and iOS
- Supports H.264, H.265/HEVC, ProRes, AV1 (M3+)
- Accessible via `hevc_videotoolbox` encoder in FFmpeg

## Feature Support by Chip Generation

| Feature | M1 | M2 | M3 | M4 |
|---------|:--:|:--:|:--:|:--:|
| H.264 Encode/Decode | ✓ | ✓ | ✓ | ✓ |
| HEVC Encode/Decode | ✓ | ✓ | ✓ | ✓ |
| ProRes Encode/Decode | ✓ | ✓ | ✓ | ✓ |
| AV1 Decode | ✗ | ✗ | ✓ | ✓ |
| ProRes RAW | ✗ | ✓ | ✓ | ✓ |
| 10-bit HEVC | ✓ | ✓ | ✓ | ✓ |

### Additional Features in Pro/Max Chips

> "Max chips have additional video encoding engines. VideoToolbox utilizes these extra engines even for a single transcoding session, supporting 4K 120fps transcoding."
> — [Jellyfin Documentation](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/apple/)

## Performance Comparison

### Software vs Hardware Encoding

| Encoder | 30s 4K Video Processing Time | File Size | Quality |
|---------|------------------------------|-----------|---------|
| libx265 (Software) | 287s | Baseline | Best |
| hevc_videotoolbox | 12s | +20-30% | Good |

> "On M2 Pro (10-core CPU/16-core GPU), VideoToolbox is **24x faster** at 287s vs 12s."
> — [b.27p.de](https://b.27p.de/p/00016-ffmpeg-apple-silicon-h265-encoding/)

### Simultaneous Transcoding Capability

> "Even the entry-level M1 can handle three 4K 24fps Dolby Vision HEVC 10-bit transcoding jobs simultaneously."
> — [Jellyfin Documentation](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/apple/)

## FFmpeg Commands

### Basic Hardware Encoding

```bash
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -q:v 50 \
  -c:a copy \
  output.mp4
```

### Recommended Settings (Quality Priority)

```bash
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -q:v 45 \
  -profile:v main \
  -tag:v hvc1 \
  -c:a copy \
  -map_metadata 0 \
  output.mp4
```

## Quality Settings Guide

### `-q:v` Option (1-100)

| Value | Quality | Use Case |
|-------|---------|----------|
| 1-30 | Highest | Archiving, original-grade |
| 40-55 | **Recommended** | General use |
| 60-75 | Medium | Storage savings |
| 80+ | Low | Not recommended |

> "hevc_videotoolbox quality 45-55 is the sweet spot. The default quality setting is not good."
> — [Hardware Encoding Guide](https://b.27p.de/p/00016-ffmpeg-apple-silicon-h265-encoding/)

### Bitrate Settings (Alternative)

```bash
# Fixed bitrate (VBR is more recommended)
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -b:v 10M \
  output.mp4

# Average bitrate
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -b:v 8M \
  -maxrate 12M \
  -bufsize 16M \
  output.mp4
```

## Software vs Hardware: Selection Guide

### Hardware Encoding (hevc_videotoolbox) Recommended For

✅ Large batch conversions
✅ When fast processing is needed
✅ Near real-time conversion required
✅ When power efficiency matters (laptops)

### Software Encoding (libx265) Recommended For

✅ Highest quality needed (archiving)
✅ Minimum file size needed
✅ No time constraints
✅ Advanced encoding options needed

## Hybrid Approach

### Step 1: Quick Conversion with Hardware

```bash
# First, fast hardware encoding
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -q:v 40 \
  -c:a copy \
  quick_output.mp4
```

### Step 2: Re-encode Important Files with Software

```bash
# High-quality software encoding for important files
ffmpeg -i input.mp4 \
  -c:v libx265 \
  -crf 20 \
  -preset slow \
  -c:a copy \
  high_quality_output.mp4
```

## 10-bit HEVC Encoding

### 10-bit Support on Apple Silicon

```bash
ffmpeg -i input.mp4 \
  -c:v hevc_videotoolbox \
  -profile:v main10 \
  -q:v 45 \
  output_10bit.mp4
```

## Utilizing VideoToolbox Decoding

### Hardware Decoding + Software Encoding Combination

```bash
# Hardware-accelerated decoding only (maintain best quality encoding)
ffmpeg -hwaccel videotoolbox \
  -i input.mp4 \
  -c:v libx265 \
  -crf 22 \
  -preset slow \
  output.mp4
```

## Limitations and Considerations

### Unsupported Options

Hardware encoders don't support all software encoder options:

❌ `-preset` (slow, medium, etc.)
❌ `-tune`
❌ `-x265-params`
❌ Some advanced GOP settings

### File Size Trade-off

> "In most cases, hardware encoding produces larger output files than software libraries. However, hardware encoding is much faster."
> — [Martin Riedl](https://www.martin-riedl.de/2020/12/06/using-hardware-acceleration-on-macos-with-ffmpeg/)

### Quality Controversy

> "Some users think VideoToolbox quality is lower (but it's incredibly fast)."
> — [MacRumors Forums](https://forums.macrumors.com/threads/apple-silicon-video-converter.2269415/page-3)

## Benchmark Script

```bash
#!/bin/bash
# Hardware vs Software encoding comparison

INPUT="test_video.mp4"

echo "=== Software Encoding (libx265) ==="
time ffmpeg -i "$INPUT" \
  -c:v libx265 -crf 23 -preset medium \
  -c:a copy \
  software_output.mp4 2>/dev/null

echo ""
echo "=== Hardware Encoding (VideoToolbox) ==="
time ffmpeg -i "$INPUT" \
  -c:v hevc_videotoolbox -q:v 50 \
  -c:a copy \
  hardware_output.mp4 2>/dev/null

echo ""
echo "=== File Size Comparison ==="
ls -lh software_output.mp4 hardware_output.mp4
```

## FFmpeg Installation Verification

```bash
# Check VideoToolbox support
ffmpeg -encoders 2>/dev/null | grep videotoolbox

# Expected output:
# V....D hevc_videotoolbox    VideoToolbox H.265 Encoder
# V....D h264_videotoolbox    VideoToolbox H.264 Encoder
```

## References

- [CodeTV - Hardware Acceleration on Apple Silicon](https://codetv.dev/blog/hardware-acceleration-ffmpeg-apple-silicon)
- [Jellyfin - Apple Hardware Acceleration](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/apple/)
- [Martin Riedl - Hardware Acceleration on macOS](https://www.martin-riedl.de/2020/12/06/using-hardware-acceleration-on-macos-with-ffmpeg/)
- [originell.org - FFmpeg Apple Hardware Acceleration](https://www.originell.org/til/ffmpeg-apple-hardware-accelerated/)
- [Codec Wiki - VideoToolbox](https://wiki.x266.mov/docs/encoders_hw/videotoolbox)
