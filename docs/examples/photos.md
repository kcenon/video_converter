# Photos Integration Examples

Examples for working with macOS Photos library.

## Preview the Library

### Dry Run (Preview)

Use `--dry-run` to preview what would be converted without making changes:

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

### Detailed Preview with Limit

```bash
video-converter run --source photos --dry-run --limit 10
```

**Output:**
```
Scanning Photos library...

Preview (first 10 of 89 videos):
  1. vacation_2024.mp4 (1.2 GB) - H.264
  2. family_dinner.mp4 (890 MB) - H.264
  ...

Use 'video-converter run --source photos' to convert all 89 videos.
```

## Album-Based Conversion

### Single Album

```bash
video-converter run --source photos --albums "Vacation 2024"
```

### Multiple Albums

```bash
video-converter run --source photos --albums "Vacation 2024,Summer Trip,Family Events"
```

### Exclude Albums

```bash
# Exclude system albums
video-converter run --source photos --exclude-albums "Screenshots,Bursts,Slo-mo"
```

## iCloud Video Handling

### Check iCloud Status

```bash
video-converter scan --mode photos --show-icloud
```

**Output:**
```
iCloud Videos:
  • vacation_day1.mp4 (1.2 GB) - In Cloud
  • trip_highlight.mp4 (890 MB) - In Cloud
  • family_2024.mp4 (2.1 GB) - Downloading...

Total iCloud-only: 12 videos (8.5 GB)
```

### Download and Convert

```bash
# Download iCloud videos before converting
video-converter run --mode photos --download-icloud
```

**Output:**
```
Downloading iCloud videos...
  [████████░░░░░░░░░░░░] 40% | vacation_day1.mp4 (480 MB / 1.2 GB)

Download complete: 12 videos (8.5 GB)
Starting conversion...
```

### Skip iCloud Videos

```bash
video-converter run --mode photos --local-only
```

## Metadata Preservation

### Verify GPS After Conversion

```bash
# Check GPS preservation
video-converter verify-metadata output.mp4 --check gps
```

**Output:**
```
Metadata Verification:
  ✅ GPS Latitude: 37.7749
  ✅ GPS Longitude: -122.4194
  ✅ GPS Altitude: 15m
  ✅ Creation Date: 2024-12-20 14:30:22
```

### Export Metadata Report

```bash
video-converter run --mode photos --metadata-report metadata.json
```

## Re-import to Photos

!!! warning "Experimental"
    Re-importing is experimental. Always keep backups.

### Convert and Re-import

```bash
video-converter run --mode photos --reimport
```

**Output:**
```
Converting and re-importing to Photos...

[1/45] vacation_2024.mp4
  Converting: [████████████████████] 100%
  Re-importing to Photos...
  ✅ Imported as: IMG_1234.mp4

[2/45] family_dinner.mp4
  Converting: [████████████████████] 100%
  Re-importing to Photos...
  ✅ Imported as: IMG_1235.mp4
```

### Skip Duplicates

```bash
video-converter run --mode photos --reimport --skip-duplicates
```

## Photos Library Statistics

### View Statistics

```bash
video-converter stats --mode photos
```

**Output:**
```
╭─────────────────────────────────────────────╮
│      Photos Library Conversion Stats         │
├─────────────────────────────────────────────┤
│  Total converted:    89 videos               │
│  Space saved:        37.5 GB                 │
│  Average savings:    52%                     │
├─────────────────────────────────────────────┤
│  Last 30 days:                               │
│    Converted: 23 videos                      │
│    Saved: 12.3 GB                            │
├─────────────────────────────────────────────┤
│  Pending conversion: 0 videos                │
│  Remaining H.264:    0                       │
╰─────────────────────────────────────────────╯
```

## Complete Workflow Example

```bash
#!/bin/bash
# Complete Photos library conversion workflow

echo "Step 1: Scanning library..."
video-converter scan --mode photos

echo "Step 2: Dry run..."
video-converter run --mode photos --dry-run

read -p "Proceed with conversion? (y/n) " confirm
if [ "$confirm" != "y" ]; then
    exit 0
fi

echo "Step 3: Converting..."
video-converter run --mode photos \
    --concurrent 2 \
    --exclude-album "Screenshots" \
    --exclude-album "Bursts"

echo "Step 4: Generating report..."
video-converter stats --mode photos --format json > conversion_report.json

echo "Complete!"
```
