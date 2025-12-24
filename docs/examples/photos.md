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

!!! note "iCloud Videos"
    Videos stored only in iCloud are automatically skipped during conversion.
    To convert iCloud videos, first download them to your Mac through Photos app.

## Metadata Preservation

Video Converter automatically preserves all metadata during conversion.

### Verify GPS After Conversion

Use `exiftool` to verify metadata preservation:

```bash
# Check GPS and date preservation
exiftool -GPS* -CreateDate converted_video.mp4
```

**Output:**
```
GPS Latitude: 37.7749 N
GPS Longitude: 122.4194 W
Create Date: 2024-12-20 14:30:22
```

## Re-import to Photos

!!! warning "Experimental"
    Re-importing is experimental. Always keep backups.

### Convert and Re-import

```bash
video-converter run --source photos --reimport
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

### Archive Originals

```bash
# Archive originals to a specific album
video-converter run --source photos --reimport --archive-album "Old H.264 Videos"
```

## View Statistics

```bash
video-converter stats --detailed
```

**Output:**
```
╭─────────────────────────────────────────────╮
│        Conversion Statistics                 │
├─────────────────────────────────────────────┤
│  Total converted:    89 videos               │
│  Space saved:        37.5 GB                 │
│  Average savings:    52%                     │
╰─────────────────────────────────────────────╯
```

## Complete Workflow Example

```bash
#!/bin/bash
# Complete Photos library conversion workflow

echo "Step 1: Preview library..."
video-converter run --source photos --dry-run

read -p "Proceed with conversion? (y/n) " confirm
if [ "$confirm" != "y" ]; then
    exit 0
fi

echo "Step 2: Converting..."
video-converter run --source photos \
    --max-concurrent 2 \
    --exclude-albums "Screenshots,Bursts"

echo "Step 3: Generating report..."
video-converter stats --json > conversion_report.json

echo "Complete!"
```
