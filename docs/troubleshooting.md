# Troubleshooting

Common issues and solutions.

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
