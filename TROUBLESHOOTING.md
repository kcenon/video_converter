# Troubleshooting Guide

Common issues and solutions for Video Converter.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Conversion Errors](#conversion-errors)
- [Service and Automation](#service-and-automation)
- [Performance Issues](#performance-issues)
- [Metadata Issues](#metadata-issues)

---

## Installation Issues

### FFmpeg Not Found

**Symptom:**
```
Error: FFmpeg not found. Please install FFmpeg.
```

**Solution:**
```bash
# Install FFmpeg via Homebrew
brew install ffmpeg

# Verify installation
ffmpeg -version
```

### ExifTool Not Found

**Symptom:**
```
Error: ExifTool not found. Metadata preservation will be disabled.
```

**Solution:**
```bash
# Install ExifTool via Homebrew
brew install exiftool

# Verify installation
exiftool -ver
```

### Python Version Error

**Symptom:**
```
Error: Python 3.10 or later is required.
```

**Solution:**
```bash
# Check your Python version
python3 --version

# Install Python 3.10+ via Homebrew
brew install python@3.12

# Use pyenv for version management (recommended)
brew install pyenv
pyenv install 3.12
pyenv global 3.12
```

---

## Conversion Errors

### Input File Not Found

**Symptom:**
```
Error: Input file not found: /path/to/video.mp4
```

**Causes:**
- File path is incorrect
- File has been moved or deleted
- iCloud file not downloaded locally

**Solutions:**
1. Verify the file path exists:
   ```bash
   ls -la /path/to/video.mp4
   ```

2. For iCloud files, download first:
   ```bash
   brctl download /path/to/video.mp4
   ```

### Permission Denied

**Symptom:**
```
Error: Permission denied: /path/to/video.mp4
```

**Solutions:**
1. Check file permissions:
   ```bash
   ls -la /path/to/video.mp4
   ```

2. Grant read permission:
   ```bash
   chmod +r /path/to/video.mp4
   ```

3. For Photos Library access, ensure Terminal/app has Full Disk Access in System Preferences > Security & Privacy > Privacy.

### Disk Space Full

**Symptom:**
```
Error: Insufficient disk space. 500 MB free, 1 GB required.
```

**Solutions:**
1. Free up disk space by removing unnecessary files
2. Move output to a drive with more space:
   ```bash
   video-converter config-set paths.output /Volumes/ExternalDrive/Converted
   ```
3. Enable cleanup of originals after successful conversion (use with caution)

### Hardware Encoder Unavailable

**Symptom:**
```
Error: VideoToolbox encoder not available.
```

**Causes:**
- Running on non-Apple hardware
- macOS version too old
- Hardware encoder busy

**Solutions:**
1. Use software encoding:
   ```bash
   video-converter convert video.mp4 --mode software
   ```

2. Set software mode as default:
   ```bash
   video-converter config-set encoding.mode software
   ```

### Encoding Failed

**Symptom:**
```
Error: FFmpeg encoding failed with exit code 1.
```

**Solutions:**
1. Try software encoding:
   ```bash
   video-converter convert video.mp4 --mode software
   ```

2. Lower quality setting:
   ```bash
   video-converter convert video.mp4 --quality 50
   ```

3. Check video file integrity:
   ```bash
   ffprobe /path/to/video.mp4
   ```

4. Enable verbose logging to see detailed error:
   ```bash
   video-converter -v convert video.mp4
   ```

### Validation Failed

**Symptom:**
```
Error: Output validation failed. Compression ratio too low.
```

**Causes:**
- Source video already highly compressed
- Quality setting too low
- Video already in H.265 format

**Solutions:**
1. The converter automatically retries with adjusted settings
2. Skip validation if needed:
   ```bash
   video-converter convert video.mp4 --no-validate
   ```

3. Check if video is already H.265:
   ```bash
   ffprobe -v error -select_streams v:0 -show_entries stream=codec_name video.mp4
   ```

---

## Service and Automation

### Service Not Starting

**Symptom:**
```
Service status: Not Running
```

**Solutions:**
1. Check if service is loaded:
   ```bash
   video-converter status
   ```

2. Reload the service:
   ```bash
   video-converter service-unload
   video-converter service-load
   ```

3. Check for errors in logs:
   ```bash
   video-converter service-logs --stderr
   ```

### Service Not Running on Schedule

**Symptom:**
Service is installed but doesn't run at scheduled time.

**Solutions:**
1. Check schedule configuration:
   ```bash
   video-converter status
   ```

2. Verify launchd plist:
   ```bash
   cat ~/Library/LaunchAgents/com.videoconverter.service.plist
   ```

3. Check macOS sleep settings (service won't run if Mac is asleep)

4. Reinstall service:
   ```bash
   video-converter uninstall-service
   video-converter install-service --time 03:00
   ```

### Cannot Uninstall Service

**Symptom:**
```
Error: Failed to uninstall service.
```

**Solution:**
```bash
# Manual uninstallation
launchctl unload ~/Library/LaunchAgents/com.videoconverter.service.plist
rm ~/Library/LaunchAgents/com.videoconverter.service.plist
```

---

## Performance Issues

### Conversion Too Slow

**Causes:**
- Using software encoding instead of hardware
- System under heavy load
- Processing very high resolution video

**Solutions:**
1. Ensure hardware mode is enabled:
   ```bash
   video-converter config
   # Check encoding.mode is "hardware"
   ```

2. Use fast preset for quicker encoding:
   ```bash
   video-converter convert video.mp4 --preset fast
   ```

3. Limit concurrent conversions:
   ```bash
   video-converter config-set processing.max_concurrent 1
   ```

### High Memory Usage

**Solutions:**
1. Reduce concurrent conversions:
   ```bash
   video-converter config-set processing.max_concurrent 1
   ```

2. Process smaller batches of files

3. Close other memory-intensive applications

### Mac Overheating During Conversion

**Solutions:**
1. Use software encoding (less GPU intensive):
   ```bash
   video-converter convert video.mp4 --mode software
   ```

2. Limit concurrent jobs:
   ```bash
   video-converter config-set processing.max_concurrent 1
   ```

3. Schedule conversions for cooler times (night):
   ```bash
   video-converter install-service --time 03:00
   ```

---

## Metadata Issues

### GPS Coordinates Not Preserved

**Symptom:**
Converted video loses location information.

**Solutions:**
1. Ensure ExifTool is installed:
   ```bash
   exiftool -ver
   ```

2. Enable metadata preservation (default):
   ```bash
   video-converter convert video.mp4 --preserve-metadata
   ```

3. Verify GPS data in original:
   ```bash
   exiftool -gps:all video.mp4
   ```

### Timestamps Not Matching

**Symptom:**
Creation date or modification date differs after conversion.

**Solutions:**
1. Timestamps are preserved by default. Check if original has valid timestamps:
   ```bash
   exiftool -time:all video.mp4
   ```

2. On macOS, birth time (creation date) requires the `SetFile` command from Xcode Command Line Tools:
   ```bash
   xcode-select --install
   ```

### ExifTool Errors

**Symptom:**
```
Warning: ExifTool failed to copy metadata.
```

**Solutions:**
1. Update ExifTool:
   ```bash
   brew upgrade exiftool
   ```

2. Check file permissions on both input and output

3. Conversion still succeeds even if metadata copy fails (video is kept)

---

## Getting More Help

### Enable Debug Logging

```bash
video-converter -v convert video.mp4
```

### View Full Logs

```bash
# View service logs
video-converter service-logs -n 100

# Follow logs in real-time
video-converter service-logs -f
```

### Check Configuration

```bash
video-converter config
```

### Reset Configuration

```bash
# Remove config file to reset
rm ~/.config/video_converter/config.json

# Run setup again
video-converter setup
```

### Report an Issue

If you've tried the above solutions and still have problems:

1. Gather information:
   ```bash
   video-converter --version
   ffmpeg -version
   exiftool -ver
   sw_vers  # macOS version
   ```

2. Open an issue at: https://github.com/kcenon/video_converter/issues

Include:
- Error message (full output)
- Steps to reproduce
- Your environment (macOS version, Python version)
- Relevant configuration settings
