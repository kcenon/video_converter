# Batch Processing Examples

Examples for processing multiple videos efficiently.

## Folder Batch Conversion

### Basic Folder Conversion

```bash
video-converter run --mode folder --path ~/Videos
```

**Output:**
```
Scanning ~/Videos...
Found 25 H.264 videos (total: 45.2 GB)

Processing: [1/25] vacation_2024.mp4
[████████████████████] 100% | 2.1 GB → 920 MB

Processing: [2/25] family_dinner.mp4
[████████████████████] 100% | 1.8 GB → 780 MB

...

╭─────────────────────────────────────────────╮
│           Batch Conversion Complete          │
├─────────────────────────────────────────────┤
│  Processed:   25 videos                      │
│  Success:     24                             │
│  Skipped:     0                              │
│  Failed:      1                              │
├─────────────────────────────────────────────┤
│  Original:    45.2 GB                        │
│  Converted:   19.8 GB                        │
│  Saved:       25.4 GB (56%)                  │
│  Duration:    1h 23m                         │
╰─────────────────────────────────────────────╯
```

### With Concurrency

```bash
# Process 4 files simultaneously
video-converter run --mode folder --path ~/Videos --concurrent 4
```

### Recursive with Structure Preservation

```bash
video-converter run --mode folder \
    --path ~/Videos \
    --recursive \
    --preserve-structure \
    --output ~/Videos/Converted
```

## Photos Library Batch

### Full Library Conversion

```bash
video-converter run --mode photos
```

### Filter by Album

```bash
# Specific album
video-converter run --mode photos --album "Vacation 2024"

# Multiple albums
video-converter run --mode photos --album "Vacation 2024" --album "Family Events"

# Exclude albums
video-converter run --mode photos --exclude-album "Screenshots" --exclude-album "Slow-mo"
```

### Filter by Date Range

```bash
# Last 6 months
video-converter run --mode photos --from "2024-06-01"

# Specific date range
video-converter run --mode photos --from "2024-01-01" --to "2024-06-30"
```

### With Size Filter

```bash
# Only large files (>100MB)
video-converter run --mode photos --min-size 100MB
```

## Dry Run

Preview what would be converted without actually converting:

```bash
video-converter run --mode photos --dry-run
```

**Output:**
```
DRY RUN - No files will be converted

Would process 45 videos:

  1. vacation_beach.mp4          (2.1 GB → ~920 MB)
  2. birthday_party.mp4          (1.5 GB → ~660 MB)
  3. concert_2024.mp4            (3.2 GB → ~1.4 GB)
  ...

Estimated total:
  Current size:  67.5 GB
  After convert: ~29.7 GB
  Space saved:   ~37.8 GB (56%)
```

## Progress Tracking

### JSON Output for Scripting

```bash
video-converter run --mode photos --output-format json > progress.json
```

### Watch Mode

```bash
# In another terminal
watch -n 5 'video-converter progress'
```

## Resume Interrupted Conversion

```bash
# List sessions
video-converter sessions

# Resume last session
video-converter resume

# Resume specific session
video-converter resume --session-id abc123
```

**Output:**
```
Resuming session abc123...
Previously completed: 15/45 videos
Continuing from: [16/45] family_dinner.mp4
```

## Scheduled Batch Processing

```bash
# Install automation
video-converter install --time 03:00

# Configure to run with specific options
video-converter config set automation.mode photos
video-converter config set automation.concurrent 2
video-converter config set automation.min_size 50MB
```

## Error Recovery

### Skip Failed and Continue

```bash
video-converter run --mode photos --skip-on-error
```

### Retry Failed Videos

```bash
video-converter retry-failed
```

### Get Detailed Error Report

```bash
video-converter run --mode photos --error-report errors.json
```
