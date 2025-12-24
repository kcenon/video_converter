# Troubleshooting

Common issues and solutions.

## GUI Application Issues

### App Won't Launch

**Cause:** macOS security settings or missing dependencies.

**Solutions:**

1. **Check macOS version** - Requires macOS 12.0 (Monterey) or later
2. **Allow in Security Settings:**
   - Go to **System Settings** > **Privacy & Security**
   - Scroll to "App was blocked from opening"
   - Click **Open Anyway**
3. **Reset quarantine attribute:**
   ```bash
   xattr -d com.apple.quarantine /Applications/Video\ Converter.app
   ```

### "Video Converter" is Damaged (Gatekeeper Error)

**Cause:** App not signed or quarantine flag set.

**Solution:**
```bash
xattr -cr /Applications/Video\ Converter.app
```

### Photos Library Access Denied

**Cause:** App doesn't have Photos permission.

**Solution:**
1. Open **System Settings** > **Privacy & Security** > **Photos**
2. Enable Video Converter in the list
3. Restart Video Converter

!!! tip
    If Video Converter doesn't appear in the list, launch the app and try accessing the Photos tab first.

### GUI Appears Frozen

**Cause:** Large batch conversion or memory pressure.

**Solutions:**

1. **Wait a moment** - UI may be updating
2. **Reduce concurrent conversions** in Settings (try 1)
3. **Check Activity Monitor** for memory usage
4. **Force quit and restart:**
   ```bash
   killall "Video Converter"
   ```

### Menubar Icon Not Appearing

**Cause:** Menubar disabled or system resources.

**Solutions:**

1. Check **Settings** > **Notification Settings** > **Show in Menubar**
2. Restart the application
3. Check if menubar is full (use Bartender or similar)

### Drag and Drop Not Working

**Cause:** Permission or file type issue.

**Solutions:**

1. Ensure file is a supported format (`.mp4`, `.mov`, `.avi`, `.mkv`, `.m4v`)
2. Check **System Settings** > **Privacy & Security** > **Files and Folders**
3. Grant Video Converter access to your files

### Queue Stuck in "Converting" State

**Cause:** FFmpeg process hung or crashed.

**Solutions:**

1. Click **Cancel All** in Queue tab
2. Check for FFmpeg processes:
   ```bash
   ps aux | grep ffmpeg
   killall ffmpeg
   ```
3. Restart Video Converter

### Window Too Small or Off-Screen

**Cause:** Saved window position is invalid.

**Solution:** Reset window position:
```bash
defaults delete com.video-converter.app NSWindow.Frame
```

---

## Installation Issues

### "FFmpeg not found"

**Solution:**
```bash
brew install ffmpeg
```

### "ExifTool not found"

**Solution:**
```bash
brew install exiftool
```

### "osxphotos import error"

**Solution:**
```bash
pip install --upgrade osxphotos
```

## Photos Library Issues

### "Photos library access denied"

**Cause:** Terminal doesn't have Photos access permission.

**Solution:**
1. Open **System Preferences** > **Privacy & Security** > **Photos**
2. Enable access for your terminal application
3. Restart the terminal

### "No videos found in Photos library"

**Causes:**
- Photos library might be empty
- Videos are iCloud-only

**Solution:**
```bash
# Check library status
video-converter scan --mode photos --verbose

# Include iCloud videos (will download)
video-converter run --mode photos --download-icloud
```

## Conversion Issues

### "Conversion fails with VideoToolbox error"

**Cause:** Hardware encoder initialization failed.

**Solution:**
```bash
# Try software encoder
video-converter convert input.mp4 output.mp4 --encoder software
```

### "Output file is larger than input"

**Cause:** Source video is already highly compressed.

**Solution:**
```bash
# Increase quality setting (reduce file size)
video-converter convert input.mp4 output.mp4 --quality 55
```

### "Conversion is very slow"

**Cause:** Using software encoder or system is under load.

**Solutions:**
```bash
# Ensure hardware encoder is used
video-converter convert input.mp4 output.mp4 --encoder hardware

# Reduce concurrent conversions
video-converter run --mode photos --concurrent 1
```

## Metadata Issues

### "GPS coordinates lost after conversion"

**Cause:** ExifTool couldn't copy GPS data.

**Solution:**
```bash
# Verify ExifTool is installed
exiftool -ver

# Re-apply metadata manually
exiftool -tagsFromFile original.mp4 "-GPS*" converted.mp4
```

### "Creation date changed"

**Solution:**
```bash
# Sync timestamps manually
touch -r original.mp4 converted.mp4
```

## Performance Issues

### "High memory usage"

**Solution:**
```bash
# Reduce concurrent conversions
video-converter run --mode photos --concurrent 1
```

### "System becomes unresponsive"

**Solutions:**
```bash
# Use nice to lower priority
nice -n 10 video-converter run --mode photos

# Limit concurrent operations
video-converter run --mode photos --concurrent 1
```

## Getting Help

If issues persist:

1. Check logs: `~/.local/share/video_converter/logs/`
2. Run with verbose output: `video-converter --verbose`
3. [Open an issue](https://github.com/kcenon/video_converter/issues)
