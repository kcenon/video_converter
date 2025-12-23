# Basic Examples

Simple conversion examples to get started.

## Single File Conversion

### Default Settings

```bash
video-converter convert input.mp4 output.mp4
```

**Expected output:**
```
Analyzing: input.mp4
  Codec: H.264 (AVC)
  Resolution: 1920x1080
  Duration: 5:32
  Size: 1.5 GB

Converting: input.mp4
[████████████████████] 100% | Speed: 6.2x | ETA: 0:00
✅ Complete: 1.5GB → 680MB (55% saved)
```

### With Quality Settings

```bash
# Higher quality (larger file)
video-converter convert input.mp4 output.mp4 --quality 30

# Lower quality (smaller file)
video-converter convert input.mp4 output.mp4 --quality 60
```

### Software Encoder

```bash
# High quality with software encoder
video-converter convert input.mp4 output.mp4 --encoder software --crf 20
```

## Multiple Files

### Using Shell Loop

```bash
for file in *.mp4; do
    video-converter convert "$file" "converted/${file%.mp4}_hevc.mp4"
done
```

### Using xargs

```bash
find . -name "*.mp4" -print0 | xargs -0 -I {} video-converter convert {} {}_hevc.mp4
```

## Check Video Properties

### Before Conversion

```bash
video-converter info input.mp4
```

**Output:**
```
╭─────────────────────────────────────────────╮
│           Video Information                 │
├─────────────────────────────────────────────┤
│  File:       input.mp4                      │
│  Codec:      H.264 (AVC)                    │
│  Resolution: 3840x2160 (4K)                 │
│  FPS:        30.0                           │
│  Duration:   10:25                          │
│  Size:       4.2 GB                         │
│  Bitrate:    56 Mbps                        │
│  Audio:      AAC 48kHz stereo               │
│  Container:  MP4                            │
├─────────────────────────────────────────────┤
│  GPS:        37.7749°N, 122.4194°W          │
│  Created:    2024-12-20 14:30:22            │
│  Device:     iPhone 15 Pro                  │
╰─────────────────────────────────────────────╯
```

### Compare Before and After

```bash
# Check both files
video-converter info input.mp4 output.mp4 --compare
```

**Output:**
```
╭──────────────────────────────────────────────────────────────╮
│                   Comparison                                  │
├──────────────────────────────────────────────────────────────┤
│                    │ Original        │ Converted              │
├──────────────────────────────────────────────────────────────┤
│  Codec             │ H.264           │ HEVC                   │
│  Size              │ 4.2 GB          │ 1.8 GB                 │
│  Bitrate           │ 56 Mbps         │ 24 Mbps                │
│  Resolution        │ 3840x2160       │ 3840x2160 ✓            │
│  Duration          │ 10:25           │ 10:25 ✓                │
│  GPS               │ Present         │ Present ✓              │
├──────────────────────────────────────────────────────────────┤
│  Space Saved: 2.4 GB (57%)                                    │
╰──────────────────────────────────────────────────────────────╯
```

## Verify Conversion

### Check Integrity

```bash
video-converter verify output.mp4
```

### With VMAF

```bash
video-converter verify input.mp4 output.mp4 --vmaf
```

**Output:**
```
╭─────────────────────────────────────────────╮
│           Verification Result               │
├─────────────────────────────────────────────┤
│  Integrity:   ✅ Valid                      │
│  Playable:    ✅ Yes                        │
│  Duration:    ✅ Matches (10:25)            │
│  Resolution:  ✅ Matches (3840x2160)        │
│  VMAF Score:  94.2 (Excellent)              │
╰─────────────────────────────────────────────╯
```

## Error Handling

### Already HEVC

```bash
video-converter convert hevc_video.mp4 output.mp4
```

**Output:**
```
⚠️ Video is already HEVC encoded. No conversion needed.
Use --force to convert anyway.
```

### Corrupted File

```bash
video-converter convert corrupted.mp4 output.mp4
```

**Output:**
```
❌ Error: Input file appears to be corrupted or incomplete.
Run 'ffprobe corrupted.mp4' for details.
```
