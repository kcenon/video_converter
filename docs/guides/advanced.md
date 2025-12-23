# Advanced Usage

Advanced features and configurations.

## Quality Tuning

### Hardware Encoder Quality Scale

| Quality Value | Description | Use Case |
|---------------|-------------|----------|
| 20-35 | High quality | Archival, important videos |
| 35-50 | Balanced | General use (default: 45) |
| 50-70 | Smaller files | Storage optimization |
| 70-100 | Minimum size | Previews, drafts |

```bash
# Archival quality
video-converter convert input.mp4 output.mp4 --quality 25

# Storage optimization
video-converter convert input.mp4 output.mp4 --quality 60
```

### Software Encoder (libx265)

| CRF | Description | Bitrate Reduction |
|-----|-------------|-------------------|
| 18 | Visually lossless | ~20% |
| 20 | Excellent quality | ~40% |
| 22 | Good quality | ~50% (default) |
| 24 | Acceptable | ~60% |
| 28 | Low quality | ~70% |

```bash
# Visually lossless
video-converter convert input.mp4 output.mp4 --encoder software --crf 18

# Maximum compression
video-converter convert input.mp4 output.mp4 --encoder software --crf 28
```

### Presets (Software Encoder)

| Preset | Speed | Compression |
|--------|-------|-------------|
| ultrafast | Fastest | Lowest |
| veryfast | Very fast | Low |
| fast | Fast | Below average |
| medium | Medium | Average (default) |
| slow | Slow | Above average |
| slower | Slower | High |
| veryslow | Very slow | Highest |

```bash
# Fast encoding, larger file
video-converter convert input.mp4 output.mp4 --encoder software --preset fast

# Maximum compression, slow
video-converter convert input.mp4 output.mp4 --encoder software --preset veryslow
```

## VMAF Quality Validation

### Enable VMAF Checking

```bash
video-converter convert input.mp4 output.mp4 --vmaf
```

### Set VMAF Threshold

```bash
# Require VMAF score >= 90
video-converter convert input.mp4 output.mp4 --vmaf --vmaf-threshold 90
```

### VMAF Score Interpretation

| Score | Quality |
|-------|---------|
| 93+ | Excellent (imperceptible difference) |
| 85-93 | Good (minor differences) |
| 75-85 | Fair (noticeable differences) |
| < 75 | Poor (significant degradation) |

## Concurrent Processing

### Resource Management

```bash
# Limit to 1 concurrent (low resource usage)
video-converter run --mode photos --concurrent 1

# Maximum parallelism (high resource usage)
video-converter run --mode photos --concurrent 4
```

### CPU/Memory Considerations

| Concurrent | CPU Usage | Memory | Recommended For |
|------------|-----------|--------|-----------------|
| 1 | Low | ~500MB | Background, shared systems |
| 2 | Medium | ~1GB | Default, balanced |
| 4 | High | ~2GB | Dedicated conversion |

## Session Recovery

Video Converter tracks conversion sessions for recovery:

```bash
# Resume interrupted session
video-converter resume

# Resume specific session
video-converter resume --session-id abc123

# List sessions
video-converter sessions
```

## Custom FFmpeg Options

```bash
# Pass custom FFmpeg options
video-converter convert input.mp4 output.mp4 \
    --ffmpeg-opts "-vf scale=1920:-1"
```

## Scripting and Integration

### JSON Output

```bash
# Get results as JSON
video-converter run --mode photos --output-format json > results.json

# Statistics as JSON
video-converter stats --format json
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | File not found |
| 4 | Conversion failed |
| 5 | Validation failed |

### Example Script

```bash
#!/bin/bash
# convert_and_notify.sh

video-converter run --mode photos --quiet

if [ $? -eq 0 ]; then
    osascript -e 'display notification "Conversion complete" with title "Video Converter"'
else
    osascript -e 'display notification "Conversion failed" with title "Video Converter"'
fi
```

## Performance Optimization

### Disk I/O

```bash
# Use SSD for temp files
export VIDEO_CONVERTER_TEMP=/Volumes/FastSSD/temp
video-converter run --mode photos
```

### Memory

```bash
# Limit memory usage
export VIDEO_CONVERTER_MAX_MEMORY=4G
video-converter run --mode photos
```

## Debugging

### Verbose Mode

```bash
video-converter run --mode photos --verbose
```

### Debug Mode

```bash
VIDEO_CONVERTER_LOG_LEVEL=DEBUG video-converter run --mode photos
```

### FFmpeg Logs

```bash
video-converter convert input.mp4 output.mp4 --ffmpeg-loglevel verbose
```
