# Automation Guide

Set up automated video conversion with launchd.

## Overview

Video Converter can run automatically using macOS launchd, allowing:

- Scheduled daily/weekly conversions
- Background processing
- Notifications on completion

## Quick Setup

```bash
# Install with default settings (daily at 3 AM)
video-converter install
```

## Custom Schedule

### Specific Time

```bash
# Run at 2:30 AM
video-converter install --time 02:30
```

### Specific Days

```bash
# Weekdays only
video-converter install --time 03:00 --days weekdays

# Weekends only
video-converter install --time 10:00 --days weekends

# Specific day
video-converter install --time 03:00 --day sunday
```

### Multiple Times

```bash
# Morning and evening
video-converter install --times "06:00,22:00"
```

## Service Management

### Check Status

```bash
video-converter status
```

**Output:**
```
Video Converter Automation
─────────────────────────
Status:    Active
Schedule:  Daily at 03:00
Last Run:  2024-12-23 03:00:12 (Success)
Next Run:  2024-12-24 03:00:00

Recent Activity:
  • 12 videos converted
  • 8.5 GB saved
  • 0 errors
```

### Start/Stop Service

```bash
# Stop service temporarily
video-converter service stop

# Start service
video-converter service start

# Restart service
video-converter service restart
```

### Uninstall

```bash
video-converter uninstall
```

## Configuration

### Automation Settings

```json
{
  "automation": {
    "enabled": true,
    "schedule": {
      "time": "03:00",
      "days": "daily"
    },
    "mode": "photos",
    "concurrent": 2,
    "notification": true,
    "log_retention_days": 30
  }
}
```

### Notification Settings

```json
{
  "notification": {
    "enabled": true,
    "on_start": false,
    "on_complete": true,
    "on_error": true,
    "sound": true
  }
}
```

## launchd Plist

The service creates a plist at:
```
~/Library/LaunchAgents/com.user.videoconverter.plist
```

### Example Plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.videoconverter</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/video-converter</string>
        <string>run</string>
        <string>--mode</string>
        <string>photos</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>~/.local/share/video_converter/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>~/.local/share/video_converter/logs/stderr.log</string>
</dict>
</plist>
```

## Logs

### Log Location

```
~/.local/share/video_converter/logs/
```

### View Logs

```bash
# Recent logs
video-converter logs

# Last 100 lines
video-converter logs --lines 100

# Follow logs (real-time)
video-converter logs --follow

# Errors only
video-converter logs --level error
```

## Troubleshooting

### Service Not Running

```bash
# Check if loaded
launchctl list | grep videoconverter

# Reload service
launchctl unload ~/Library/LaunchAgents/com.user.videoconverter.plist
launchctl load ~/Library/LaunchAgents/com.user.videoconverter.plist
```

### Permission Issues

Ensure Photos access is granted:
1. System Preferences > Privacy & Security > Photos
2. Enable access for Terminal and launchd

### Debugging

```bash
# Run manually to test
video-converter run --mode photos --verbose
```
