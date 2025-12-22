# Processing Procedures Definition

## 1. Overall Processing Procedure Overview

### 1.1 Main Workflow

```mermaid
flowchart TB
    START([Start]) --> INIT[System Initialization]
    INIT --> LOAD_CONFIG[Load Configuration]
    LOAD_CONFIG --> CHECK_DEPS{Check Dependencies}

    CHECK_DEPS -->|Failed| ERROR_DEPS[Report Dependency Error]
    ERROR_DEPS --> END_FAIL([End - Failed])

    CHECK_DEPS -->|Success| SCAN[Scan Photos Library]

    SCAN --> FILTER[Filter H.264 Videos]
    FILTER --> EXCLUDE[Exclude Already Converted]

    EXCLUDE --> CHECK_QUEUE{Targets Available?}
    CHECK_QUEUE -->|None| LOG_EMPTY[Log No Targets]
    LOG_EMPTY --> END_SUCCESS([End - Success])

    CHECK_QUEUE -->|Available| ESTIMATE[Estimate Time]
    ESTIMATE --> PROCESS_LOOP[Start Batch Processing]

    subgraph "Batch Processing Loop"
        PROCESS_LOOP --> NEXT_VIDEO{Next Video?}
        NEXT_VIDEO -->|Yes| EXPORT[Export Video]
        EXPORT --> CONVERT[Convert to H.265]
        CONVERT --> VALIDATE[Quality Validation]
        VALIDATE --> RESTORE_META[Restore Metadata]
        RESTORE_META --> MOVE_ORIG[Process Original]
        MOVE_ORIG --> UPDATE_STATS[Update Statistics]
        UPDATE_STATS --> NEXT_VIDEO
    end

    NEXT_VIDEO -->|No| GENERATE_REPORT[Generate Report]
    GENERATE_REPORT --> NOTIFY[Send Notification]
    NOTIFY --> CLEANUP[Clean Temp Files]
    CLEANUP --> END_SUCCESS
```

### 1.2 Processing Stage Details

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Processing Procedure Summary                       │
├─────────┬───────────────────────────────────────────────────────────────┤
│ Stage   │ Description                                                     │
├─────────┼───────────────────────────────────────────────────────────────┤
│ 1. Init │ Load config, check dependencies, create directories            │
│ 2. Scan │ Collect video list from Photos library                         │
│ 3. Filter│ Select H.264 only, exclude already converted                  │
│ 4. Export│ Export original from Photos to temp directory                 │
│ 5. Convert│ Execute H.265 encoding with FFmpeg                           │
│ 6. Validate│ Verify output file integrity and quality                    │
│ 7. Metadata│ Restore GPS, dates, and other metadata                      │
│ 8. Cleanup│ Move/delete original, record stats, notify                   │
└─────────┴───────────────────────────────────────────────────────────────┘
```

## 2. Detailed Stage Procedures

### 2.1 System Initialization Procedure

```mermaid
flowchart TB
    subgraph "1. Load Configuration"
        A1[Load Default Config] --> A2[Merge User Config]
        A2 --> A3[Override with Env Vars]
        A3 --> A4[Override with CLI Args]
        A4 --> A5[Validate Config]
    end

    subgraph "2. Check Dependencies"
        B1[Check FFmpeg Installed] --> B2[Check Version Compatibility]
        B2 --> B3[Check VideoToolbox Support]
        B3 --> B4[Check ExifTool Installed]
        B4 --> B5[Check osxphotos Installed]
        B5 --> B6[Check Python Version]
    end

    subgraph "3. Prepare Directories"
        C1[Verify Input Directory] --> C2[Create Output Directory]
        C2 --> C3[Create Processed Directory]
        C3 --> C4[Create Failed Directory]
        C4 --> C5[Create Log Directory]
    end

    subgraph "4. Initialize Logging"
        D1[Configure Log File] --> D2[Set Log Level]
        D2 --> D3[Configure Log Rotation]
    end

    A5 --> B1
    B6 --> C1
    C5 --> D1
```

#### Dependency Check Script

```bash
#!/bin/bash
# check_dependencies.sh

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: $1 is not installed"
        return 1
    fi
    echo "OK: $1 found at $(which $1)"
    return 0
}

check_ffmpeg_hevc() {
    if ffmpeg -encoders 2>/dev/null | grep -q hevc_videotoolbox; then
        echo "OK: hevc_videotoolbox encoder available"
        return 0
    fi
    echo "ERROR: hevc_videotoolbox not available"
    return 1
}

echo "=== Checking Dependencies ==="

check_command ffmpeg
check_command ffprobe
check_command exiftool
check_command python3

python3 -c "import osxphotos" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "OK: osxphotos module available"
else
    echo "ERROR: osxphotos module not installed"
fi

check_ffmpeg_hevc

echo "=== Dependency Check Complete ==="
```

### 2.2 Video Scan and Filter Procedure

```mermaid
flowchart TB
    subgraph "Photos Library Scan"
        S1[Connect PhotosDB] --> S2[Query All Media]
        S2 --> S3[Filter Videos Only]
        S3 --> S4[Create VideoInfo Objects]
    end

    subgraph "Codec Analysis"
        F1[Check Codec with FFprobe] --> F2{H.264?}
        F2 -->|Yes| F3[Add to Conversion List]
        F2 -->|No| F4[Skip]
    end

    subgraph "Exclude Duplicates"
        E1[Load Conversion History] --> E2[Scan Output Folder]
        E2 --> E3[Match Filenames]
        E3 --> E4{Already Converted?}
        E4 -->|Yes| E5[Exclude from List]
        E4 -->|No| E6[Add to Final List]
    end

    S4 --> F1
    F3 --> E1
```

#### Codec Detection Function

```python
def detect_codec(video_path: Path) -> str:
    """Detect video codec using FFprobe"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=codec_name',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip().lower()


def is_h264(video_path: Path) -> bool:
    """Check if codec is H.264"""
    codec = detect_codec(video_path)
    return codec in ('h264', 'avc', 'avc1')


def is_already_hevc(video_path: Path) -> bool:
    """Check if already HEVC codec"""
    codec = detect_codec(video_path)
    return codec in ('hevc', 'h265', 'hvc1', 'hev1')
```

### 2.3 Video Conversion Procedure

```mermaid
flowchart TB
    subgraph "Conversion Preparation"
        P1[Validate Input File] --> P2[Generate Output Path]
        P2 --> P3[Set Temp File Path]
        P3 --> P4[Determine Encoding Options]
    end

    subgraph "FFmpeg Execution"
        E1[Build FFmpeg Command] --> E2[Start Process]
        E2 --> E3[Monitor Progress]
        E3 --> E4{Complete?}
        E4 -->|In Progress| E3
        E4 -->|Done| E5{Success?}
    end

    subgraph "Result Processing"
        R1[Verify Output File] --> R2[Move Temp to Final]
        R2 --> R3[Create Result Object]
    end

    subgraph "Error Handling"
        X1[Analyze Error] --> X2{Retry?}
        X2 -->|Yes| X3[Wait and Retry]
        X2 -->|No| X4[Handle Failure]
    end

    P4 --> E1
    E5 -->|Success| R1
    E5 -->|Failed| X1
    X3 --> E1
```

#### FFmpeg Command Builder

```python
def build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    config: EncodingConfig
) -> List[str]:
    """Build FFmpeg command based on encoding configuration"""

    cmd = ['ffmpeg', '-y', '-i', str(input_path)]

    if config.mode == 'hardware':
        # VideoToolbox hardware encoding
        cmd.extend([
            '-c:v', 'hevc_videotoolbox',
            '-q:v', str(config.quality),  # 1-100
            '-tag:v', 'hvc1',  # QuickTime compatibility
        ])
    else:
        # libx265 software encoding
        cmd.extend([
            '-c:v', 'libx265',
            '-crf', str(config.crf),  # 0-51
            '-preset', config.preset,
        ])

    # Common options
    cmd.extend([
        '-c:a', 'copy',           # Copy audio stream
        '-map_metadata', '0',      # Copy metadata
        '-movflags', 'use_metadata_tags',
        '-progress', 'pipe:1',     # Progress output
        str(output_path)
    ])

    return cmd
```

### 2.4 Metadata Restoration Procedure

```mermaid
flowchart TB
    subgraph "Metadata Extraction"
        M1[Read Original File] --> M2[Run ExifTool]
        M2 --> M3[Parse JSON]
        M3 --> M4[Create Metadata Object]
    end

    subgraph "Metadata Application"
        A1[ExifTool -tagsFromFile] --> A2[Verify GPS Coordinates]
        A2 --> A3[Verify Date/Time]
        A3 --> A4[Verify Camera Info]
    end

    subgraph "Timestamp Sync"
        T1[Read Original Timestamps] --> T2[Set Creation Date]
        T2 --> T3[Set Modification Date]
        T3 --> T4[Set Access Date]
    end

    subgraph "Verification"
        V1[Read Converted File Metadata] --> V2{Match?}
        V2 -->|Yes| V3[Success]
        V2 -->|No| V4[Log Warning]
    end

    M4 --> A1
    A4 --> T1
    T4 --> V1
```

#### Metadata Restoration Script

```bash
#!/bin/bash
# restore_metadata.sh

ORIGINAL="$1"
CONVERTED="$2"

echo "Restoring metadata from $ORIGINAL to $CONVERTED"

# 1. Copy all tags with ExifTool
exiftool -overwrite_original \
    -tagsFromFile "$ORIGINAL" \
    -all:all \
    "$CONVERTED"

# 2. Explicitly copy GPS info (may be missed in some formats)
exiftool -overwrite_original \
    -tagsFromFile "$ORIGINAL" \
    "-GPS*" \
    "$CONVERTED"

# 3. Sync file timestamps
touch -r "$ORIGINAL" "$CONVERTED"

# 4. Verify results
echo "=== Original Metadata ==="
exiftool -CreateDate -GPSLatitude -GPSLongitude "$ORIGINAL"

echo "=== Converted Metadata ==="
exiftool -CreateDate -GPSLatitude -GPSLongitude "$CONVERTED"
```

### 2.5 Quality Validation Procedure

```mermaid
flowchart TB
    subgraph "Basic Validation"
        B1[Check File Exists] --> B2[Check File Size]
        B2 --> B3[FFprobe Integrity Check]
        B3 --> B4{Basic Validation Pass?}
    end

    subgraph "Property Comparison"
        P1[Compare Resolution] --> P2[Compare Framerate]
        P2 --> P3[Compare Duration]
        P3 --> P4{Properties Match?}
    end

    subgraph "Quality Validation (Optional)"
        Q1[Calculate VMAF] --> Q2{VMAF >= 93?}
        Q2 -->|Yes| Q3[Pass]
        Q2 -->|No| Q4[Warning/Fail]
    end

    subgraph "Compression Ratio Check"
        C1[Original Size / Converted Size] --> C2{Normal Range?}
        C2 -->|20-80%| C3[Normal]
        C2 -->|Out of Range| C4[Warning]
    end

    B4 -->|Yes| P1
    B4 -->|No| FAIL[Validation Failed]

    P4 -->|Yes| Q1
    P4 -->|No| FAIL

    Q3 --> C1
    Q4 --> C1

    C3 --> SUCCESS[Validation Success]
    C4 --> SUCCESS
```

#### Quality Validation Function

```python
def validate_conversion(
    original: Path,
    converted: Path,
    config: ValidationConfig
) -> ValidationResult:
    """Validate conversion result"""

    errors = []
    warnings = []

    # 1. Check file existence and size
    if not converted.exists():
        return ValidationResult(valid=False, errors=["Output file not found"])

    if converted.stat().st_size == 0:
        return ValidationResult(valid=False, errors=["Output file is empty"])

    # 2. FFprobe integrity check
    probe_result = run_ffprobe(converted)
    if probe_result.get('error'):
        return ValidationResult(valid=False, errors=["File integrity check failed"])

    # 3. Property comparison
    orig_info = get_video_info(original)
    conv_info = get_video_info(converted)

    if abs(orig_info.duration - conv_info.duration) > 1.0:
        errors.append(f"Duration mismatch: {orig_info.duration} vs {conv_info.duration}")

    if orig_info.resolution != conv_info.resolution:
        errors.append(f"Resolution mismatch: {orig_info.resolution} vs {conv_info.resolution}")

    # 4. Compression ratio check
    compression = converted.stat().st_size / original.stat().st_size
    if compression < 0.2 or compression > 0.8:
        warnings.append(f"Unusual compression ratio: {compression:.2%}")

    # 5. VMAF calculation (if configured)
    vmaf_score = None
    if config.validate_quality:
        vmaf_score = calculate_vmaf(original, converted)
        if vmaf_score < config.min_vmaf:
            errors.append(f"VMAF score too low: {vmaf_score}")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        vmaf_score=vmaf_score,
        compression_ratio=compression
    )
```

## 3. Automation Procedures

### 3.1 launchd Service Setup Procedure

```mermaid
flowchart TB
    subgraph "Installation"
        I1[Create plist File] --> I2[Copy to LaunchAgents]
        I2 --> I3[Run launchctl load]
        I3 --> I4[Verify Service Status]
    end

    subgraph "Execution Flow"
        R1[Trigger Occurred] --> R2[launchd Runs Script]
        R2 --> R3[Script Complete]
        R3 --> R4[Wait ThrottleInterval]
        R4 --> R1
    end

    subgraph "Monitoring"
        M1[Check Status with launchctl list] --> M2[Check Log Files]
        M2 --> M3[Check System Logs]
    end

    subgraph "Removal"
        U1[launchctl unload] --> U2[Delete plist File]
        U2 --> U3[Clean Logs]
    end
```

### 3.2 Complete Installation Script

```bash
#!/bin/bash
# install.sh - Video Converter Installation Script

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/bin/video_converter"
CONFIG_DIR="$HOME/.config/video_converter"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
PLIST_NAME="com.user.videoconverter.plist"

echo "=== Video Converter Installation ==="

# 1. Install dependencies
echo "1. Installing dependencies..."
if ! command -v brew &> /dev/null; then
    echo "Homebrew is required. Please install it."
    exit 1
fi

brew install ffmpeg exiftool python@3.12

# 2. Install Python packages
echo "2. Installing Python packages..."
pip3 install osxphotos

# 3. Install application
echo "3. Installing application..."
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/src/"* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/"*.sh

# 4. Create configuration file
echo "4. Creating configuration file..."
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cat > "$CONFIG_DIR/config.json" << 'EOF'
{
  "version": "0.1.0.0",
  "encoding": {
    "mode": "hardware",
    "quality": 45
  },
  "paths": {
    "output": "~/Videos/Converted",
    "processed": "~/Videos/Processed",
    "failed": "~/Videos/Failed"
  },
  "automation": {
    "schedule": "daily",
    "time": "03:00"
  }
}
EOF
fi

# 5. Create directories
echo "5. Creating work directories..."
mkdir -p ~/Videos/{ToConvert,Converted,Processed,Failed}
mkdir -p ~/Library/Logs/video_converter

# 6. Install launchd service
echo "6. Installing automation service..."
mkdir -p "$LAUNCH_AGENTS"

cat > "$LAUNCH_AGENTS/$PLIST_NAME" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.videoconverter</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$INSTALL_DIR/main.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/video_converter/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/video_converter/stderr.log</string>
</dict>
</plist>
EOF

launchctl load "$LAUNCH_AGENTS/$PLIST_NAME"

echo ""
echo "=== Installation Complete ==="
echo "- Install location: $INSTALL_DIR"
echo "- Config file: $CONFIG_DIR/config.json"
echo "- Log location: ~/Library/Logs/video_converter/"
echo ""
echo "Auto-execution scheduled at 3:00 AM daily."
echo "Manual execution: python3 $INSTALL_DIR/main.py"
```

## 4. Operations Procedures

### 4.1 Daily Operations Checklist

```
□ 1. Check service status
    $ launchctl list | grep videoconverter

□ 2. Check recent logs
    $ tail -100 ~/Library/Logs/video_converter/stdout.log

□ 3. Check error logs
    $ cat ~/Library/Logs/video_converter/stderr.log

□ 4. Check disk space
    $ df -h ~/Videos

□ 5. Check pending files
    $ ls ~/Videos/ToConvert/

□ 6. Check failed files
    $ ls ~/Videos/Failed/
```

### 4.2 Troubleshooting Procedure

```mermaid
flowchart TB
    PROBLEM[Problem Occurred] --> CHECK_SERVICE{Service Running?}

    CHECK_SERVICE -->|No| START_SERVICE[Start Service]
    START_SERVICE --> RECHECK{Resolved?}
    RECHECK -->|Yes| DONE[Done]
    RECHECK -->|No| CHECK_LOGS

    CHECK_SERVICE -->|Yes| CHECK_LOGS[Check Logs]

    CHECK_LOGS --> IDENTIFY{Error Type?}

    IDENTIFY -->|Permission Error| FIX_PERM[Fix Permissions]
    IDENTIFY -->|Disk Space| CLEANUP[Free Space]
    IDENTIFY -->|FFmpeg Error| CHECK_FFMPEG[Check FFmpeg]
    IDENTIFY -->|Photos Error| CHECK_PHOTOS[Check Photos Access]

    FIX_PERM --> RETRY[Retry]
    CLEANUP --> RETRY
    CHECK_FFMPEG --> RETRY
    CHECK_PHOTOS --> RETRY

    RETRY --> DONE
```

## 5. Summary Diagrams

### 5.1 Overall System Flow Summary

```mermaid
graph LR
    subgraph "Input"
        A[Photos Library]
        B[Watch Folder]
    end

    subgraph "Processing"
        C[Extractor]
        D[Detector]
        E[Converter]
        F[Validator]
        G[Metadata]
    end

    subgraph "Output"
        H[Converted Videos]
        I[Reports]
        J[Notifications]
    end

    A --> C
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    G --> I
    G --> J
```

### 5.2 Core Processing Stages

```
┌──────────────────────────────────────────────────────────────────┐
│                    Video Converter Processing Pipeline             │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐          │
│  │ SCAN    │ → │ FILTER  │ → │ EXPORT  │ → │ CONVERT │          │
│  │ Photos  │   │ H.264   │   │ to Temp │   │ H.265   │          │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘          │
│       ↓                                          ↓                │
│  ┌─────────┐                              ┌─────────┐            │
│  │ REPORT  │ ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ← │VALIDATE │            │
│  │ & NOTIFY│                              │ Quality │            │
│  └─────────┘                              └─────────┘            │
│       ↓                                          ↓                │
│  ┌─────────┐                              ┌─────────┐            │
│  │ CLEANUP │ ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ← │METADATA │            │
│  │ Originals│                             │ Restore │            │
│  └─────────┘                              └─────────┘            │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```
