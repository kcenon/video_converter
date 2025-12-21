# macOS Automation Methods Guide

## Overview

This document covers various methods for implementing video conversion automation on macOS.

## Automation Method Comparison

| Method | Complexity | Reliability | Flexibility | Recommended Use |
|--------|------------|-------------|-------------|-----------------|
| Folder Actions | Low | Medium | Low | Simple automation |
| Automator | Low | Medium | Medium | GUI-based workflows |
| launchd | Medium | High | High | Daemon/background tasks |
| Shell Script + cron | Low | High | High | Periodic tasks |
| Hazel (Third-party) | Low | High | High | Advanced folder monitoring |

## Method 1: Folder Actions

### Introduction

> "The ability to watch folders and take action on incoming items is a powerful automation technique that enables completely unattended workflows."
> — [Apple Developer](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/WatchFolders.html)

### Setup Method

1. Control-click target folder in Finder
2. Select **Services** → **Folder Actions Setup**
3. Attach script

### AppleScript Example: Video Conversion Trigger

```applescript
-- ~/Library/Scripts/Folder Action Scripts/ConvertToHEVC.scpt

on adding folder items to this_folder after receiving added_items
    repeat with this_item in added_items
        set item_path to POSIX path of this_item
        set file_ext to name extension of (info for this_item)

        if file_ext is in {"mp4", "mov", "m4v", "MP4", "MOV", "M4V"} then
            -- Execute FFmpeg conversion
            set output_path to item_path & "_hevc.mp4"
            set cmd to "/opt/homebrew/bin/ffmpeg -i " & quoted form of item_path
            set cmd to cmd & " -c:v hevc_videotoolbox -q:v 50 -c:a copy "
            set cmd to cmd & quoted form of output_path

            do shell script cmd
        end if
    end repeat
end adding folder items to
```

### Limitations

> "Folder Actions work well when manually adding files, but may not work when files 'appear' synced from other devices through iCloud."
> — [Automators Talk](https://talk.automators.fm/t/watch-folder-with-automator-and-icloud/7864)

## Method 2: Automator Folder Action

### Setup Steps

1. Launch **Automator** app (⌘ + Space → "Automator")
2. **New Document** → Select **Folder Action**
3. Specify target folder at top
4. Add **Run Shell Script** action

### Automator Workflow Example

```bash
#!/bin/bash
# Automator "Run Shell Script" action
# Select "Pass input: as arguments"

for file in "$@"; do
    # Check file extension
    ext="${file##*.}"
    ext_lower=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

    if [[ "$ext_lower" == "mp4" || "$ext_lower" == "mov" || "$ext_lower" == "m4v" ]]; then
        # Set output path
        dir=$(dirname "$file")
        name=$(basename "$file" ".$ext")
        output="${dir}/${name}_hevc.mp4"

        # FFmpeg conversion
        /opt/homebrew/bin/ffmpeg -i "$file" \
            -c:v hevc_videotoolbox \
            -q:v 50 \
            -c:a copy \
            -map_metadata 0 \
            "$output" 2>&1

        # Restore metadata
        /opt/homebrew/bin/exiftool -tagsFromFile "$file" "$output" 2>/dev/null
    fi
done
```

### Save Location

Workflow save locations:
- All users: `/Library/Workflows/Applications/Folder Actions/`
- Current user: `~/Library/Workflows/Applications/Folder Actions/`

## Method 3: launchd (Recommended)

### Introduction

launchd is macOS's service management framework and the most reliable automation method.

> "You can watch folders by setting the WatchPaths property on a launchd job. It's a bit more cumbersome to set up but more reliable."
> — [Automators Talk](https://talk.automators.fm/t/watch-folder-with-automator-and-icloud/7864)

### Folder Monitoring with WatchPaths

#### 1. Create Conversion Script

```bash
#!/bin/bash
# ~/Scripts/convert_to_hevc.sh

WATCH_DIR="$HOME/Videos/ToConvert"
OUTPUT_DIR="$HOME/Videos/Converted"
PROCESSED_DIR="$HOME/Videos/Processed"
LOG_FILE="$HOME/Videos/conversion.log"

mkdir -p "$OUTPUT_DIR" "$PROCESSED_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

for file in "$WATCH_DIR"/*.{mp4,mov,m4v,MP4,MOV,M4V} 2>/dev/null; do
    [ -f "$file" ] || continue

    filename=$(basename "$file")
    name="${filename%.*}"
    output="$OUTPUT_DIR/${name}_hevc.mp4"

    log "Converting: $filename"

    /opt/homebrew/bin/ffmpeg -i "$file" \
        -c:v hevc_videotoolbox \
        -q:v 45 \
        -tag:v hvc1 \
        -c:a copy \
        -map_metadata 0 \
        -movflags use_metadata_tags \
        "$output" 2>> "$LOG_FILE"

    if [ $? -eq 0 ]; then
        # Restore metadata
        /opt/homebrew/bin/exiftool -tagsFromFile "$file" "$output" 2>/dev/null
        touch -r "$file" "$output"

        # Move original
        mv "$file" "$PROCESSED_DIR/"
        log "Completed: $filename"
    else
        log "Failed: $filename"
    fi
done
```

#### 2. Create launchd plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.videoconverter</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/username/Scripts/convert_to_hevc.sh</string>
    </array>

    <key>WatchPaths</key>
    <array>
        <string>/Users/username/Videos/ToConvert</string>
    </array>

    <key>RunAtLoad</key>
    <false/>

    <key>StandardOutPath</key>
    <string>/Users/username/Videos/launchd_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/username/Videos/launchd_stderr.log</string>

    <key>ThrottleInterval</key>
    <integer>30</integer>
</dict>
</plist>
```

#### 3. Register and Start Service

```bash
# Copy plist
cp com.user.videoconverter.plist ~/Library/LaunchAgents/

# Load service
launchctl load ~/Library/LaunchAgents/com.user.videoconverter.plist

# Check status
launchctl list | grep videoconverter

# Unload service (if needed)
launchctl unload ~/Library/LaunchAgents/com.user.videoconverter.plist
```

### Periodic Execution (StartInterval)

```xml
<!-- Run every hour -->
<key>StartInterval</key>
<integer>3600</integer>
```

### Scheduled Execution (StartCalendarInterval)

```xml
<!-- Run daily at 2 AM -->
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>2</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

## Method 4: Shell Script + Cron

### crontab Setup

```bash
# Edit crontab
crontab -e

# Run conversion script every hour
0 * * * * /Users/username/Scripts/convert_to_hevc.sh

# Run daily at 11 PM
0 23 * * * /Users/username/Scripts/convert_to_hevc.sh
```

### Real-time Monitoring with fswatch

```bash
# Install fswatch
brew install fswatch

# Real-time folder monitoring
fswatch -0 ~/Videos/ToConvert | xargs -0 -n 1 ~/Scripts/convert_single.sh
```

## Method 5: Hazel (Third-party)

### Introduction

> "Hazel is a third-party app by Noodlesoft, an enhanced version of Folder Actions. Available for $42."
> — [Macworld](https://www.macworld.com/article/634271/attach-action-mac-folder.html)

### Advantages

- Complex condition settings possible
- Easy rule creation with GUI
- Filtering based on file properties
- Detects iCloud synced files

### Rule Example

1. **Condition**: Extension is mp4, mov, m4v
2. **Condition**: Filename doesn't contain "_hevc"
3. **Action**: Execute shell script

## Photos Library Auto-Conversion Workflow

### osxphotos + launchd Integration

```bash
#!/bin/bash
# ~/Scripts/photos_to_hevc.sh

EXPORT_DIR="$HOME/Videos/PhotosExport"
CONVERTED_DIR="$HOME/Videos/Converted"
LOG_FILE="$HOME/Videos/photos_conversion.log"

mkdir -p "$EXPORT_DIR" "$CONVERTED_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 1. Export videos not yet converted
log "Exporting new videos from Photos..."

osxphotos export "$EXPORT_DIR" \
    --only-movies \
    --skip-edited \
    --update \
    --download-missing \
    2>> "$LOG_FILE"

# 2. Convert exported videos
for file in "$EXPORT_DIR"/*.{mp4,mov,m4v,MP4,MOV,M4V} 2>/dev/null; do
    [ -f "$file" ] || continue

    filename=$(basename "$file")
    name="${filename%.*}"

    # Skip already converted files
    if [ -f "$CONVERTED_DIR/${name}_hevc.mp4" ]; then
        continue
    fi

    log "Converting: $filename"

    /opt/homebrew/bin/ffmpeg -i "$file" \
        -c:v hevc_videotoolbox \
        -q:v 45 \
        -tag:v hvc1 \
        -c:a copy \
        -map_metadata 0 \
        "$CONVERTED_DIR/${name}_hevc.mp4" 2>> "$LOG_FILE"

    if [ $? -eq 0 ]; then
        /opt/homebrew/bin/exiftool -tagsFromFile "$file" "$CONVERTED_DIR/${name}_hevc.mp4" 2>/dev/null
        log "Completed: $filename"
    else
        log "Failed: $filename"
    fi
done

log "Batch conversion completed"
```

### Daily Execution with launchd

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.photos-hevc-converter</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/username/Scripts/photos_to_hevc.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

## Security Considerations

### Permissions Since macOS Mojave

> "Starting with macOS Mojave, workflows containing AppleScript/JavaScript require user security approval on first run."
> — [Apple Developer](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/WatchFolders.html)

### Full Disk Access Permission

To access the Photos library:

1. **System Settings** → **Privacy & Security** → **Full Disk Access**
2. Add Terminal or script

## Debugging and Monitoring

### Check launchd Logs

```bash
# Check service status
launchctl list | grep videoconverter

# Check system logs
log show --predicate 'subsystem == "com.apple.launchd"' --last 1h

# Check script logs
tail -f ~/Videos/conversion.log
```

### Add Notifications

```bash
# macOS notification on conversion complete
osascript -e 'display notification "Video conversion complete" with title "Video Converter"'
```

## References

- [Apple - Mac Automation Scripting Guide](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/WatchFolders.html)
- [macosxautomation.com - Folder Actions](http://www.macosxautomation.com/automator/folder-action/index.html)
- [Six Colors - Shortcuts with Folder Actions](https://sixcolors.com/post/2023/08/generation-gap-using-shortcuts-with-folder-actions/)
- [Simple Help - Folder Actions Explained](https://www.simplehelp.net/2007/01/30/folder-actions-for-os-x-explained-with-real-world-examples/)
