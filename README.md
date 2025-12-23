# Video Converter

[![CI](https://github.com/kcenon/video_converter/actions/workflows/ci.yml/badge.svg)](https://github.com/kcenon/video_converter/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/kcenon/video_converter/branch/main/graph/badge.svg)](https://codecov.io/gh/kcenon/video_converter)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![macOS](https://img.shields.io/badge/macOS-12.0+-000000.svg)](https://apple.com/macos)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Keep your precious memories, halve your storage**

Automated video codec conversion solution for macOS that converts H.264 videos to H.265 (HEVC), achieving **50%+ storage savings** while maintaining **visually identical quality** and **preserving all metadata**.

## Features

- **Automation**: Set once, runs daily automatically via launchd
- **Lossless Quality**: VMAF 93+ (visually indistinguishable)
- **Metadata Safe**: 100% preservation of GPS, dates, album info
- **Hardware Accelerated**: Fast conversion with Apple Silicon VideoToolbox
- **Photos Integration**: Direct access to macOS Photos library
- **Notifications**: macOS Notification Center alerts for batch completion and errors

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| macOS | 12.0 (Monterey) | 14.0+ (Sonoma) |
| CPU | Apple M1 | Apple M2 Pro+ |
| RAM | 8GB | 16GB+ |
| Python | 3.10+ | 3.12+ |

## Installation

```bash
# Clone the repository
git clone https://github.com/kcenon/video_converter.git
cd video_converter

# Install dependencies
brew install ffmpeg exiftool
pip install -e .

# Grant Photos access (will prompt on first run)
video-converter setup
```

## Quick Start

### Single File Conversion

```bash
# Basic conversion (auto-generates output name with _h265 suffix)
video-converter convert input.mp4

# Specify output file
video-converter convert input.mp4 output.mp4

# High quality software encoding
video-converter convert input.mov output.mov --mode software --quality 85

# Fast encoding with preset
video-converter convert input.mp4 --preset fast

# Overwrite existing output file
video-converter convert input.mp4 output.mp4 --force

# Quiet mode for scripts
video-converter -q convert input.mp4 output.mp4

# Enable VMAF quality measurement
video-converter convert input.mp4 --vmaf

# Set custom VMAF threshold (fail if below 80)
video-converter convert input.mp4 --vmaf --vmaf-threshold 80
```

#### Progress Display

During conversion, a real-time progress bar is shown:

```
Converting: vacation.mp4
Mode: hardware (hevc_videotoolbox)
Input: 1.50 GB (H264, 4K@30fps, 3 min 45 sec)

⠋ Converting vacation.mp4 ━━━━━━━━━━━━━━━━━━━━ 30% │ 450 MB │ ETA: 2m 15s
```

#### Completion Summary

After conversion, a formatted summary is displayed:

```
╭──────────────────────────────────────────────╮
│            Conversion Complete               │
├──────────────────────────────────────────────┤
│  Input:      vacation.mp4                    │
│  Output:     vacation_h265.mp4               │
│  Codec:      H.264 → H.265 (hardware)        │
├──────────────────────────────────────────────┤
│  Original:   1.50 GB                         │
│  Converted:  680 MB                          │
│  Saved:      820 MB (54.7%)                  │
├──────────────────────────────────────────────┤
│  Duration:   3 min 45 sec                    │
│  Speed:      6.2x realtime                   │
├──────────────────────────────────────────────┤
│  VMAF: 94.2 (Visually Lossless)              │
╰──────────────────────────────────────────────╯
```

### Batch Conversion (Folder)

```bash
# Convert all videos in a directory
video-converter run --input-dir ~/Videos

# Convert recursively (include subdirectories)
video-converter run --input-dir ~/Videos -r

# Dry run to see what would be converted
video-converter run --input-dir ~/Videos --dry-run

# Specify custom output directory
video-converter run --input-dir ~/Videos --output-dir ~/Converted
```

### Batch Conversion (Photos Library)

Convert H.264 videos directly from your macOS Photos library:

```bash
# Convert all H.264 videos from Photos library
video-converter run --source photos

# Preview what would be converted (dry run)
video-converter run --source photos --dry-run

# Convert specific albums only
video-converter run --source photos --albums "Vacation,Family"

# Exclude certain albums
video-converter run --source photos --exclude-albums "Screenshots,Bursts"

# Filter by date range
video-converter run --source photos --from-date 2024-01-01 --to-date 2024-12-31

# Convert only favorite videos
video-converter run --source photos --favorites-only

# Limit number of videos to convert
video-converter run --source photos --limit 10

# Combine multiple filters
video-converter run --source photos --albums "Travel" --from-date 2024-06-01 --limit 50

# Re-import converted videos back to Photos library
video-converter run --source photos --reimport

# Re-import and archive originals (default behavior)
video-converter run --source photos --reimport --archive-album "Old H.264 Videos"

# Re-import and keep both original and converted
video-converter run --source photos --reimport --keep-originals

# Re-import and delete originals (requires confirmation)
video-converter run --source photos --reimport --delete-originals --confirm-delete
```

#### Re-import Options

When using `--reimport`, converted videos are imported back to your Photos library:

| Option | Description |
|--------|-------------|
| `--reimport` | Enable re-import of converted videos to Photos |
| `--archive-album NAME` | Archive originals to this album (default: "Converted Originals") |
| `--keep-originals` | Keep both original and converted versions |
| `--delete-originals` | Delete original videos after successful re-import |
| `--confirm-delete` | Required safety confirmation for `--delete-originals` |

By default (without `--keep-originals` or `--delete-originals`), original videos are moved to an archive album for later review.

#### Dry Run Output

```
              Photos Videos to Convert (Dry Run)
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Filename               ┃ Size    ┃ Date       ┃ Album       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ vacation_clip.mov      │ 245.3 MB│ 2024-07-15 │ Vacation    │
│ family_dinner.mp4      │ 180.2 MB│ 2024-06-20 │ Family (+2) │
│ birthday_party.mov     │ 520.8 MB│ 2024-05-10 │ Events      │
└────────────────────────┴─────────┴────────────┴─────────────┘

Total: 3 files, 946.3 MB

Run without --dry-run to start conversion.
```

#### Photos Access Permission

On first run, you'll need to grant Full Disk Access:

1. Open **System Settings** → **Privacy & Security** → **Full Disk Access**
2. Click the **+** button
3. Add **Terminal.app** (or your terminal application)
4. Enable the toggle and restart the application

You can verify permissions before running:

```bash
# Check Photos library access permission
video-converter run --source photos --check-permissions
```

If permission is denied, you'll see a helpful panel with instructions:

```
╭───────────────── Photos Library Access Denied ──────────────────╮
│                                                                  │
│  Video Converter needs Full Disk Access to read your Photos     │
│  library.                                                        │
│                                                                  │
│  To grant access:                                                │
│    1. Open System Settings → Privacy & Security                  │
│    2. Click Full Disk Access                                     │
│    3. Click the + button                                         │
│    4. Add Terminal.app (or your terminal application)            │
│    5. Enable the toggle                                          │
│    6. Restart your terminal and try again                        │
│                                                                  │
│  Quick access:                                                   │
│    open "x-apple.systempreferences:com.apple.preference          │
│    .security?Privacy_AllFiles"                                   │
│                                                                  │
╰──────────────────────────────────────────────────────────────────╯
```

#### Concurrent Processing

When converting multiple files, the converter supports concurrent processing for faster batch operations:

```bash
# Set max concurrent conversions (default: 2)
video-converter config-set processing.max_concurrent 4

# Or use environment variable
export VIDEO_CONVERTER_PROCESSING__MAX_CONCURRENT=4
video-converter run --input-dir ~/Videos
```

The concurrent processing system:
- Processes multiple videos in parallel up to the configured limit
- Monitors system resources (CPU, memory) when available
- Shows aggregated progress across all active conversions
- Maintains order of results matching input order

### Resume Interrupted Conversion

If a conversion is interrupted (system crash, restart, or manual pause), you can resume from where it left off:

```bash
# Check for resumable sessions
video-converter status --sessions

# Resume the interrupted session
video-converter run --resume
```

Session state is automatically saved to `~/.local/share/video_converter/sessions/`.

### Enable Daily Automation

```bash
# Install with default schedule (daily at 3:00 AM)
video-converter install-service

# Install with custom time
video-converter install-service --time 02:00

# Install for weekly execution (every Monday at 4:00 AM)
video-converter install-service --time 04:00 --weekday 1

# Install with folder watching
video-converter install-service --watch ~/Videos/Import

# Combine time schedule with folder watching
video-converter install-service --time 03:00 --watch ~/Videos/Import

# Force reinstall if already installed
video-converter install-service --force
```

### Check Service Status

```bash
video-converter status
```

Output example:
```
╭──────────────────────────────────────────────╮
│         Video Converter Service              │
├──────────────────────────────────────────────┤
│  Status:     ○ Idle                          │
│  Schedule:   Daily at 03:00                  │
│  Plist:      ...aunchAgents/com.videocon...  │
╰──────────────────────────────────────────────╯
```

### Remove Automation Service

```bash
# Uninstall service (with confirmation)
video-converter uninstall-service

# Uninstall without confirmation
video-converter uninstall-service --yes

# Uninstall and remove log files
video-converter uninstall-service --remove-logs
```

### Service Management Commands

Control the launchd service with these commands:

```bash
# Manually start the service (triggers immediate run)
video-converter service-start

# Stop the running service
video-converter service-stop

# Load the service into launchd (plist must be installed)
video-converter service-load

# Unload the service from launchd (keeps plist file)
video-converter service-unload

# Restart the service (unload + load)
video-converter service-restart

# View service logs (stdout)
video-converter service-logs

# View last 100 lines of logs
video-converter service-logs -n 100

# View error logs (stderr)
video-converter service-logs --stderr

# Follow logs in real-time (like tail -f)
video-converter service-logs -f
```

## Usage

```bash
video-converter <command> [options]

Commands:
  convert           Single file conversion
  run               Batch conversion execution
  status            Service and conversion status
  stats             Conversion statistics
  stats-export      Export statistics to file
  config            View current configuration
  config-set        Modify configuration values
  setup             Initial setup wizard
  install-service   Install launchd automation service
  uninstall-service Remove launchd automation service
  service-start     Manually start the service
  service-stop      Stop the running service
  service-load      Load service into launchd
  service-unload    Unload service from launchd
  service-restart   Restart the service
  service-logs      View service log files

Global Options:
  --config PATH  Custom config file path
  -v, --verbose  Detailed log output (DEBUG level)
  -q, --quiet    Minimal output (errors only)
  --version      Show version
  --help         Show help
```

### Convert Command Options

```bash
video-converter convert INPUT_FILE [OUTPUT_FILE] [options]

Arguments:
  INPUT_FILE   Path to the video file to convert (required)
  OUTPUT_FILE  Output path (optional, auto-generated if not specified)

Options:
  --mode TEXT       Encoding mode: hardware or software
  --quality INT     Quality setting 1-100 (higher = better quality, larger file)
  --preset TEXT     Encoder preset: fast, medium, slow
  -f, --force       Overwrite output file if exists
  --preserve-metadata/--no-preserve-metadata
                    Preserve original metadata (default: True)
  --validate/--no-validate
                    Validate output file after conversion (default: True)
  --vmaf/--no-vmaf  Measure VMAF quality score after conversion (default: False)
  --vmaf-threshold FLOAT
                    Minimum acceptable VMAF score (default: 93.0)
  --vmaf-sample-interval INT
                    Frame sampling interval for VMAF analysis (default: 30)
  --help            Show help
```

### View Conversion Statistics

```bash
# Show all-time statistics
video-converter stats

# Show statistics for this week
video-converter stats --period week

# Show statistics for today
video-converter stats --period today

# Show detailed statistics with recent conversions
video-converter stats --detailed

# Output statistics as JSON
video-converter stats --json
```

Output example:
```
╭────────────────────────────────────────────────╮
│           Conversion Statistics                │
├────────────────────────────────────────────────┤
│  Period: All Time (since 2024-01-01)           │
├────────────────────────────────────────────────┤
│  Videos Converted:     245                     │
│  Success Rate:         98.4%                   │
│  Total Original:       125.6 GB                │
│  Total Converted:      58.2 GB                 │
│  Storage Saved:        67.4 GB (53.7%)         │
├────────────────────────────────────────────────┤
│  Average Compression:  53.2%                   │
╰────────────────────────────────────────────────╯
```

### Export Statistics

```bash
# Export to JSON (default)
video-converter stats-export

# Export to CSV
video-converter stats-export --format csv

# Export this week's stats with records
video-converter stats-export --period week --include-records

# Export to specific file
video-converter stats-export -o ~/reports/stats.json
```

### View and Modify Configuration

```bash
# View current configuration
video-converter config

# Set encoding mode to software
video-converter config-set encoding.mode software

# Set quality level
video-converter config-set encoding.quality 60

# Set max concurrent conversions
video-converter config-set processing.max_concurrent 4
```

## Configuration

Configuration file location: `~/.config/video_converter/config.json`

```json
{
  "version": "0.2.0.0",
  "encoding": {
    "mode": "hardware",
    "quality": 45,
    "crf": 22,
    "preset": "medium",
    "bit_depth": 8,
    "hdr": false
  },
  "paths": {
    "output": "~/Videos/Converted",
    "processed": "~/Videos/Processed",
    "failed": "~/Videos/Failed"
  },
  "automation": {
    "enabled": false,
    "schedule": "daily",
    "time": "03:00"
  },
  "photos": {
    "include_albums": [],
    "exclude_albums": ["Screenshots"],
    "download_from_icloud": true,
    "reimport": false,
    "original_handling": "archive",
    "archive_album": "Converted Originals"
  },
  "processing": {
    "max_concurrent": 2,
    "validate_quality": true,
    "preserve_original": true,
    "enable_vmaf": false,
    "vmaf_threshold": 93
  },
  "folder": {
    "auto_download_icloud": true,
    "icloud_timeout": 3600,
    "skip_icloud_on_timeout": true
  },
  "notification": {
    "on_complete": true,
    "on_error": true,
    "daily_summary": false
  }
}
```

### Environment Variable Overrides

Configuration can be overridden using environment variables with the `VIDEO_CONVERTER_` prefix:

```bash
# Override encoding mode
export VIDEO_CONVERTER_ENCODING__MODE=software

# Override quality setting
export VIDEO_CONVERTER_ENCODING__QUALITY=80

# Override max concurrent jobs
export VIDEO_CONVERTER_PROCESSING__MAX_CONCURRENT=4
```

Note: Use double underscore (`__`) for nested configuration keys.

## How It Works

```
Photos Library ──▶ H.264 Detection ──▶ VideoToolbox ──▶ H.265 Output
                                           │
                                           ▼
                              Metadata Preservation (ExifTool)
                                           │
                                           ▼
                              Quality Validation (FFprobe)
```

1. **Scan**: Query H.264 videos from Photos library using osxphotos
2. **Convert**: Hardware-accelerated conversion via VideoToolbox
3. **Preserve**: Copy all metadata including GPS coordinates
4. **Validate**: Verify integrity and quality of converted files
5. **Report**: Send macOS notification with summary

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start](QUICK_START.md) | Get started in 5 minutes |
| [Troubleshooting](TROUBLESHOOTING.md) | Common issues and solutions |
| [Changelog](CHANGELOG.md) | Version history and changes |
| [PRD](docs/PRD.md) | Product Requirements Document |
| [SRS](docs/SRS.md) | Software Requirements Specification |
| [SDS](docs/SDS.md) | Software Design Specification |
| [Architecture](docs/architecture/) | System architecture and diagrams |
| [Development Plan](docs/development-plan.md) | Development phases and timeline |

## GUI Application (Preview)

> **Note**: The GUI is currently under development for v0.3.0.0

Install and run the GUI application:

```bash
# Install with GUI dependencies
pip install -e ".[gui]"

# Run the GUI application
video-converter-gui
```

Features (coming soon):
- Drag & drop video files
- Photos library browser
- Real-time conversion progress
- Menubar app for background monitoring
- Dark mode support

## Technology Stack

- **Python 3.10+**: Core application
- **FFmpeg + VideoToolbox**: Video encoding (hardware accelerated)
- **osxphotos**: macOS Photos library access
- **ExifTool**: Metadata extraction and preservation
- **launchd**: macOS native automation
- **PySide6**: GUI application (optional)

## Performance

| Video | Mode | Time | Compression |
|-------|------|------|-------------|
| 4K 30min | Hardware | ~5 min | 50-60% |
| 1080p 10min | Hardware | ~30 sec | 50-60% |
| 4K 30min | Software | ~30 min | 55-65% |

## Roadmap

> **Note**: This project uses 0.x.x.x versioning to indicate active development status.

- [x] v0.1.0.0 - CLI with automation (Released 2025-12-22)
- [x] v0.2.0.0 - VMAF quality verification, enhanced features (Released 2025-12-23)
  - [x] VMAF quality analysis (integrated into conversion pipeline)
  - [x] macOS Notification Center integration
  - [x] Statistics and reporting
  - [x] Concurrent processing
  - [x] Error recovery and retry logic
  - [x] Rich progress display
  - [x] Photos library re-import
  - [x] iCloud file support
  - [x] Enhanced service management
- [ ] v0.3.0.0 - GUI application (in development)
  - [x] Phase 1: PySide6 setup and project structure
  - [ ] Phase 2: Main window and navigation
  - [ ] Phase 3: Conversion view and progress
  - [ ] Phase 4: Photos library browser
  - [ ] Phase 5: Queue management
  - [ ] Phase 6: Settings view
  - [ ] Phase 7: Menubar app
  - [ ] Phase 8: macOS packaging
- [ ] v0.4.0.0 - AV1 codec support

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) before submitting a PR.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [FFmpeg](https://ffmpeg.org/) - Video processing
- [osxphotos](https://github.com/RhetTbull/osxphotos) - Photos library access
- [ExifTool](https://exiftool.org/) - Metadata handling
