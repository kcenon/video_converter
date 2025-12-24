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

Use `ffprobe` to check video properties:

```bash
# Check codec and format
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,duration -of csv=p=0 input.mp4

# Check metadata including GPS
exiftool -GPS* -CreateDate -Model input.mp4
```

**Example output:**
```
h264,3840,2160,625.000000
Create Date: 2024-12-20 14:30:22
GPS Latitude: 37.7749 N
GPS Longitude: 122.4194 W
Model: iPhone 15 Pro
```

## Verify Conversion with VMAF

Use the `--vmaf` option during conversion to automatically measure quality:

```bash
video-converter convert input.mp4 output.mp4 --vmaf
```

**Output includes VMAF score:**
```
╭──────────────────────────────────────────────╮
│            Conversion Complete               │
├──────────────────────────────────────────────┤
│  Input:      input.mp4                       │
│  Output:     output.mp4                      │
│  Size:       4.2 GB → 1.8 GB (57% saved)     │
│  VMAF Score: 94.2 (Excellent)                │
╰──────────────────────────────────────────────╯
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
