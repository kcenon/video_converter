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
| `--mode` | `photos` | Source mode: `photos` or `folder` |
| `--path` | - | Folder path (for folder mode) |
| `--concurrent` | `2` | Number of concurrent conversions |
| `--encoder` | `hardware` | Encoder type |
| `--dry-run` | `false` | Simulate without converting |

**Examples:**

```bash
# Convert Photos library
video-converter run --mode photos

# Convert folder
video-converter run --mode folder --path ~/Videos

# Dry run to see what would be converted
video-converter run --mode photos --dry-run
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
| `--days` | `30` | Number of days to show |
| `--format` | `table` | Output format: `table` or `json` |

### install

Install automation service.

```bash
video-converter install [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--time` | `03:00` | Run time (HH:MM) |
| `--days` | `daily` | Schedule: `daily`, `weekdays`, `weekends` |

### uninstall

Remove automation service.

```bash
video-converter uninstall
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
