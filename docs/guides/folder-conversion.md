# Folder Conversion

Convert videos from folders instead of Photos library.

## Basic Usage

```bash
video-converter run --mode folder --path /path/to/videos
```

## Scanning Folders

```bash
# Scan folder
video-converter scan --mode folder --path ~/Videos

# Scan with subdirectories
video-converter scan --mode folder --path ~/Videos --recursive
```

## Conversion Options

### Basic Folder Conversion

```bash
video-converter run --mode folder --path ~/Videos/Source
```

### Specify Output Directory

```bash
video-converter run --mode folder \
    --path ~/Videos/Source \
    --output ~/Videos/Converted
```

### Recursive Conversion

```bash
video-converter run --mode folder \
    --path ~/Videos \
    --recursive \
    --preserve-structure
```

**Input structure:**
```
~/Videos/
├── Vacation/
│   ├── day1.mp4
│   └── day2.mp4
└── Family/
    └── birthday.mp4
```

**Output structure:**
```
~/Videos/Converted/
├── Vacation/
│   ├── day1.mp4
│   └── day2.mp4
└── Family/
    └── birthday.mp4
```

## Filtering

### By Extension

```bash
# Only MP4 files
video-converter run --mode folder --path ~/Videos --extension mp4

# Multiple extensions
video-converter run --mode folder --path ~/Videos --extension mp4,mov,avi
```

### By Size

```bash
# Only files larger than 100MB
video-converter run --mode folder --path ~/Videos --min-size 100MB

# Only files smaller than 4GB
video-converter run --mode folder --path ~/Videos --max-size 4GB
```

### By Date

```bash
# Files modified after date
video-converter run --mode folder --path ~/Videos --after 2024-01-01
```

## Naming Options

### Suffix Mode

```bash
video-converter run --mode folder --path ~/Videos --suffix "_hevc"
```

Result: `video.mp4` → `video_hevc.mp4`

### Replace Mode

```bash
video-converter run --mode folder --path ~/Videos --replace
```

Result: Original is replaced (use with caution!)

### Custom Pattern

```bash
video-converter run --mode folder --path ~/Videos \
    --pattern "{name}_h265_{date}.mp4"
```

## Concurrent Processing

```bash
# Process 4 files simultaneously
video-converter run --mode folder --path ~/Videos --concurrent 4
```

## Watch Mode

Monitor folder and convert new files automatically:

```bash
video-converter watch --path ~/Videos/Input --output ~/Videos/Output
```

## Example Workflow

```bash
# 1. Scan to see what needs conversion
video-converter scan --mode folder --path ~/Videos --recursive

# 2. Dry run to verify
video-converter run --mode folder --path ~/Videos \
    --recursive --dry-run

# 3. Run conversion
video-converter run --mode folder --path ~/Videos \
    --recursive \
    --output ~/Videos/Converted \
    --concurrent 2
```
