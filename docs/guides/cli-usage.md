# CLI Usage Guide

Complete reference for Video Converter command-line interface.

## Command Structure

```bash
video-converter <command> [options] [arguments]
```

## Commands

### convert

Convert a single video file.

```bash
video-converter convert <input> [output] [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--mode` | `hardware` | Encoding mode: `hardware` or `software` |
| `--quality` | config default | Quality setting (1-100, higher = better) |
| `--preset` | `medium` | Encoder preset: `fast`, `medium`, `slow` |
| `-f, --force` | `false` | Overwrite output file if exists |
| `--vmaf` | config default | Measure VMAF quality score after conversion |

**Examples:**

```bash
# Basic conversion
video-converter convert vacation.mp4 vacation_hevc.mp4

# High quality software encoding
video-converter convert input.mp4 output.mp4 --mode software --quality 90

# Hardware encoding with custom quality
video-converter convert input.mp4 output.mp4 --quality 70
```

### run

Run batch conversion.

```bash
video-converter run [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--source` | `folder` | Source mode: `photos` or `folder` |
| `--input-dir` | - | Input directory for folder mode |
| `--output-dir` | - | Output directory for converted files |
| `-r, --recursive` | `false` | Recursively scan subdirectories |
| `--max-concurrent` | config default | Number of concurrent conversions (1-8) |
| `--dry-run` | `false` | Preview without converting |
| `--resume` | `false` | Resume previously interrupted session |

**Examples:**

```bash
# Convert Photos library
video-converter run --source photos

# Convert folder
video-converter run --source folder --input-dir ~/Videos

# Dry run to see what would be converted
video-converter run --source photos --dry-run

# Resume interrupted session
video-converter run --resume
```

### status

Show service status.

```bash
video-converter status
```

**Output:**
```
Video Converter Service Status
──────────────────────────────
Service: Active
Next run: 2024-12-24 03:00:00
Last run: 2024-12-23 03:00:00 (Success)
```

### stats

Show conversion statistics.

```bash
video-converter stats [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--period` | `all` | Time period: `today`, `week`, `month`, `all` |
| `--json` | `false` | Output statistics in JSON format |
| `--detailed` | `false` | Show detailed statistics with recent conversions |

### install-service

Install launchd automation service.

```bash
video-converter install-service [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--time` | `03:00` | Run time in HH:MM format |

### uninstall-service

Remove launchd automation service.

```bash
video-converter uninstall-service
```

## Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version |
| `--help` | Show help |
| `--verbose` | Enable verbose output |
| `--quiet` | Suppress non-error output |
| `--config` | Path to config file |

## Configuration

### Config File Location

```
~/.config/video_converter/config.json
```

### Example Configuration

```json
{
  "encoder": "hardware",
  "quality": 45,
  "concurrent": 2,
  "output_dir": "~/Videos/Converted",
  "preserve_original": true,
  "notification": true
}
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `VIDEO_CONVERTER_CONFIG` | Config file path |
| `VIDEO_CONVERTER_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `VIDEO_CONVERTER_OUTPUT_DIR` | Default output directory |
