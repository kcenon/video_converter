# Video Converter - Software Requirements Specification (SRS)

**Document Version**: 1.0.0
**Date**: 2025-12-21
**Status**: Draft
**Reference Document**: PRD v1.0.0

---

## Document Information

### Traceability Information

| Item | Reference |
|------|-----------|
| Parent Document | PRD.md v1.0.0 |
| Related Documents | SDS.md, development-plan.md, architecture/*.md |
| Requirements ID Scheme | SRS-xxx (this document), FR-xxx/NFR-xxx (PRD) |

### Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-21 | - | Initial creation |

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Overview](#2-system-overview)
3. [Functional Requirements Details](#3-functional-requirements-details)
4. [Non-Functional Requirements Details](#4-non-functional-requirements-details)
5. [External Interface Requirements](#5-external-interface-requirements)
6. [Data Requirements](#6-data-requirements)
7. [System Constraints](#7-system-constraints)
8. [Requirements Traceability Matrix](#8-requirements-traceability-matrix)
9. [Verification and Validation](#9-verification-and-validation)
10. [Appendix](#10-appendix)

---

## 1. Overview

### 1.1 Purpose

This document specifies the software requirements for the Video Converter system in detail. It provides technical specifications derived from the PRD (Product Requirements Document) at a level sufficient for the development team to implement.

### 1.2 Scope

| Item | Content |
|------|---------|
| System Name | Video Converter |
| Version | 1.0.0 |
| Target Platform | macOS 12.0+ (Apple Silicon) |
| Development Language | Python 3.10+ |

### 1.3 Definitions and Abbreviations

| Abbreviation | Definition |
|--------------|------------|
| SRS | Software Requirements Specification |
| PRD | Product Requirements Document |
| FR | Functional Requirement |
| NFR | Non-Functional Requirement |
| US | User Story |
| RTM | Requirements Traceability Matrix |
| HEVC | High Efficiency Video Coding (H.265) |
| AVC | Advanced Video Coding (H.264) |

### 1.4 Reference Documents

- PRD.md - Product Requirements Document
- **SDS.md - Software Design Specification** (Design implementation of this document)
- development-plan.md - Development Plan
- 01-system-architecture.md - System Architecture
- 02-sequence-diagrams.md - Sequence Diagrams
- 03-data-flow-and-states.md - Data Flow and States
- 04-processing-procedures.md - Processing Procedures

---

## 2. System Overview

### 2.1 System Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           System Context                                  │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │    User     │
                              │  (macOS)    │
                              └──────┬──────┘
                                     │ CLI / Notifications
                                     ▼
┌──────────────┐            ┌─────────────────┐            ┌──────────────┐
│   Photos     │───read────▶│ Video Converter │───write───▶│  File System │
│   Library    │            │     System      │            │   (Output)   │
└──────────────┘            └────────┬────────┘            └──────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
             ┌──────────┐     ┌──────────┐     ┌──────────┐
             │  FFmpeg  │     │ ExifTool │     │ launchd  │
             │ (Convert)│     │ (Meta)   │     │ (Auto)   │
             └──────────┘     └──────────┘     └──────────┘
```

### 2.2 System Functions Overview

| Function Area | Description | PRD Reference |
|---------------|-------------|---------------|
| Codec Detection | Auto-detect H.264/H.265 codec | FR-001 |
| Video Conversion | H.264 → H.265 encoding | FR-002, FR-003 |
| Photos Integration | Scan and extract from Photos library | FR-101 ~ FR-105 |
| Metadata Processing | Preserve GPS, dates, etc. | FR-201 ~ FR-204 |
| Quality Management | Verify conversion results | FR-301 ~ FR-304 |
| Automation | Schedule and folder watch execution | FR-401 ~ FR-404 |
| CLI | Command-line interface | FR-501 ~ FR-505 |
| Safety Management | Original preservation and error recovery | FR-601 ~ FR-604 |

### 2.3 User Classification

| User Type | Description | PRD Reference |
|-----------|-------------|---------------|
| General User | Basic CLI functions, relies on automation | Persona: Minsu |
| Advanced User | Detailed CLI options, quality customization | Persona: Jiyeon |
| Developer/Admin | Script integration, log analysis, service management | Persona: Sungho |

---

## 3. Functional Requirements Details

### 3.1 Codec Detection Module (SRS-100)

#### SRS-101: Video Codec Detection

| Item | Content |
|------|---------|
| **ID** | SRS-101 |
| **Name** | Video Codec Detection |
| **PRD Trace** | FR-001, US-201 |
| **Priority** | P0 (Required) |

**Description**:
The system shall detect the video stream codec of input video files.

**Preconditions**:
- Valid video file path provided
- FFprobe installed on system

**Input**:
```
Input: video_path: Path
       - Absolute path to video file
       - Supported extensions: .mp4, .mov, .m4v, .MP4, .MOV, .M4V
```

**Processing Logic**:
```python
def detect_codec(video_path: Path) -> CodecInfo:
    """
    Extract video codec info using FFprobe

    Algorithm:
    1. Construct FFprobe command
       - Select video stream only (-select_streams v:0)
       - Extract codec name (-show_entries stream=codec_name)
    2. Execute FFprobe as subprocess
    3. Parse and normalize output (lowercase)
    4. Return CodecInfo object
    """
```

**FFprobe Command**:
```bash
ffprobe -v error \
  -select_streams v:0 \
  -show_entries stream=codec_name \
  -of default=noprint_wrappers=1:nokey=1 \
  "<video_path>"
```

**Output**:
```
Output: CodecInfo
        - codec_name: str  # "h264", "hevc", "av1", etc.
        - is_h264: bool    # Is H.264
        - is_hevc: bool    # Is H.265/HEVC
```

**Codec Mapping Table**:
| FFprobe Output | Normalized Value | is_h264 | is_hevc |
|----------------|------------------|---------|---------|
| h264 | h264 | True | False |
| avc | h264 | True | False |
| avc1 | h264 | True | False |
| hevc | hevc | False | True |
| h265 | hevc | False | True |
| hvc1 | hevc | False | True |
| hev1 | hevc | False | True |

**Exception Handling**:
| Exception | Handling | Error Code |
|-----------|----------|------------|
| File not found | Raise FileNotFoundError | E-101 |
| FFprobe execution failed | Raise FFprobeError | E-102 |
| No video stream | Raise NoVideoStreamError | E-103 |
| Unknown codec | Raise UnknownCodecError | E-104 |

**Performance Requirements**:
- Single file detection time: ≤500ms
- Memory usage: ≤10MB

---

### 3.2 Video Conversion Module (SRS-200)

#### SRS-201: Hardware Accelerated Conversion (VideoToolbox)

| Item | Content |
|------|---------|
| **ID** | SRS-201 |
| **Name** | Hardware Accelerated H.265 Conversion |
| **PRD Trace** | FR-002, US-203, US-204 |
| **Priority** | P0 (Required) |

**Description**:
Convert H.264 video to H.265 using Apple Silicon's VideoToolbox for hardware acceleration.

**Preconditions**:
- Input file is H.264 codec (verified by SRS-101)
- Apple Silicon Mac (M1/M2/M3/M4)
- FFmpeg 5.0+ (hevc_videotoolbox support)

**Input**:
```
Input: ConversionRequest
       - input_path: Path      # Input video path
       - output_path: Path     # Output video path
       - quality: int          # Quality setting (1-100, default 45)
       - audio_mode: str       # "copy" | "transcode" (default "copy")
```

**Quality Setting Mapping**:
| Preset | quality Value | Expected Compression | Use Case |
|--------|---------------|---------------------|----------|
| High Quality | 30-40 | 35-45% | Archiving |
| Balanced (default) | 45-55 | 45-55% | General use |
| Fast | 60-70 | 55-65% | Bulk conversion |

**FFmpeg Command Generation**:
```python
def build_hardware_command(request: ConversionRequest) -> List[str]:
    """
    Generate FFmpeg command for hardware encoding
    """
    return [
        "ffmpeg",
        "-y",                           # Allow overwrite
        "-i", str(request.input_path),  # Input file
        "-c:v", "hevc_videotoolbox",    # VideoToolbox encoder
        "-q:v", str(request.quality),   # Quality setting
        "-tag:v", "hvc1",               # QuickTime compatible tag
        "-c:a", request.audio_mode,     # Audio handling
        "-map_metadata", "0",           # Metadata copy
        "-movflags", "use_metadata_tags",
        "-progress", "pipe:1",          # Progress output
        str(request.output_path)
    ]
```

**Progress Monitoring**:
```python
class ProgressMonitor:
    """
    FFmpeg progress parsing and callback handling

    FFmpeg progress output format:
    - out_time_ms=12500000
    - frame=375
    - fps=45.2
    - speed=3.5x
    """

    def parse_progress(self, line: str) -> Optional[ProgressInfo]:
        """
        Parse progress line

        Returns:
            ProgressInfo: Progress information
            - current_time_ms: int  # Current processed time (ms)
            - frame: int            # Processed frame count
            - fps: float            # Current processing speed
            - speed: float          # Speed relative to realtime
        """
```

**Output**:
```
Output: ConversionResult
        - success: bool           # Success flag
        - input_path: Path        # Input path
        - output_path: Path       # Output path
        - original_size: int      # Original size (bytes)
        - converted_size: int     # Converted size (bytes)
        - compression_ratio: float # Compression ratio (0.0-1.0)
        - duration_seconds: float  # Conversion duration
        - speed_ratio: float       # Speed relative to realtime
        - error_message: str       # Error message if failed
```

**Exception Handling**:
| Exception | Retry | Handling | Error Code |
|-----------|-------|----------|------------|
| FFmpeg execution failed | 3x | Exponential backoff retry | E-201 |
| Disk space insufficient | 0x | Fail immediately, notify user | E-202 |
| Input file corrupted | 0x | Move to failed folder | E-203 |
| Output file creation failed | 1x | Retry with temp directory | E-204 |
| Encoder initialization failed | 1x | Fallback to software encoder | E-205 |

**Retry Logic**:
```python
async def convert_with_retry(
    request: ConversionRequest,
    max_retries: int = 3
) -> ConversionResult:
    """
    Retry logic with exponential backoff

    Retry delays: 5s, 10s, 20s
    """
    for attempt in range(max_retries):
        try:
            result = await self._convert(request)
            if result.success:
                return result
        except RetryableError as e:
            if attempt < max_retries - 1:
                delay = 5 * (2 ** attempt)  # 5, 10, 20 seconds
                await asyncio.sleep(delay)
            else:
                raise MaxRetriesExceededError(e)
```

---

#### SRS-202: Software Conversion (libx265)

| Item | Content |
|------|---------|
| **ID** | SRS-202 |
| **Name** | Software H.265 Conversion |
| **PRD Trace** | FR-003, US-203 |
| **Priority** | P1 (Important) |

**Description**:
High-quality software encoding using libx265. Slower than hardware encoding but provides smaller file sizes and higher quality.

**FFmpeg Command Generation**:
```python
def build_software_command(request: ConversionRequest) -> List[str]:
    """
    Generate FFmpeg command for software encoding
    """
    return [
        "ffmpeg",
        "-y",
        "-i", str(request.input_path),
        "-c:v", "libx265",              # Software encoder
        "-crf", str(request.crf),        # CRF quality setting
        "-preset", request.preset,       # Encoding preset
        "-c:a", request.audio_mode,
        "-map_metadata", "0",
        "-progress", "pipe:1",
        str(request.output_path)
    ]
```

**CRF Setting Guide**:
| Use Case | CRF Value | Preset | Expected Compression | Expected VMAF |
|----------|-----------|--------|---------------------|---------------|
| Archiving | 18-20 | slow | 30-40% | 97+ |
| High Quality | 20-22 | slow | 40-50% | 95+ |
| Balanced | 22-24 | medium | 45-55% | 93+ |
| Size Priority | 24-28 | fast | 55-65% | 90+ |

---

### 3.3 Photos Integration Module (SRS-300)

#### SRS-301: Photos Library Scan

| Item | Content |
|------|---------|
| **ID** | SRS-301 |
| **Name** | Photos Library Scan |
| **PRD Trace** | FR-101, FR-102, US-201, US-205 |
| **Priority** | P0 (Required) |

**Description**:
Query the macOS Photos library video list using osxphotos and filter only H.264 codec videos.

**Preconditions**:
- osxphotos 0.70+ installed
- Photos library access permission (Full Disk Access)

**Interface**:
```python
class PhotosExtractor:
    """Extract videos from Photos library"""

    def __init__(self, library_path: Optional[Path] = None):
        """
        Parameters:
            library_path: Photos library path
                          None uses default path
                          Default: ~/Pictures/Photos Library.photoslibrary
        """

    def scan_videos(
        self,
        filter_codec: Optional[str] = "h264",
        since_date: Optional[datetime] = None,
        albums: Optional[List[str]] = None,
        exclude_converted: bool = True
    ) -> List[VideoInfo]:
        """
        Scan video list

        Parameters:
            filter_codec: Codec to filter (None for all)
            since_date: Only videos created after this date
            albums: Specific albums only (None for all)
            exclude_converted: Exclude already converted videos

        Returns:
            List of VideoInfo objects
        """

    def export_video(
        self,
        video: VideoInfo,
        dest_dir: Path,
        download_from_icloud: bool = True
    ) -> Path:
        """
        Export video file

        Parameters:
            video: Video info to export
            dest_dir: Export destination directory
            download_from_icloud: Download from iCloud if needed

        Returns:
            Exported file path
        """
```

**VideoInfo Data Structure**:
```python
@dataclass
class VideoInfo:
    """Video information data class"""

    uuid: str                           # Photos internal UUID
    original_filename: str              # Original filename
    path: Optional[Path]                # Local file path (None if iCloud)
    codec: str                          # Video codec
    duration: float                     # Duration (seconds)
    size: int                           # File size (bytes)
    width: int                          # Horizontal resolution
    height: int                         # Vertical resolution
    fps: float                          # Frame rate
    creation_date: datetime             # Capture date
    location: Optional[Tuple[float, float]]  # (latitude, longitude)
    albums: List[str]                   # Album membership
    is_in_icloud: bool                  # iCloud only flag
    is_favorite: bool                   # Favorite flag
```

---

### 3.4 Metadata Processing Module (SRS-400)

#### SRS-401: Metadata Extraction

| Item | Content |
|------|---------|
| **ID** | SRS-401 |
| **Name** | Metadata Extraction |
| **PRD Trace** | FR-201, US-301, US-302 |
| **Priority** | P0 (Required) |

**Description**:
Extract all metadata from the original video using ExifTool.

**Interface**:
```python
class MetadataManager:
    """Metadata extraction and restoration management"""

    def extract(self, video_path: Path) -> Metadata:
        """
        Extract metadata from video

        ExifTool command: exiftool -json <path>

        Returns:
            Metadata object
        """

    def apply(
        self,
        source_path: Path,
        target_path: Path,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        Copy metadata from source to target

        ExifTool command:
        exiftool -overwrite_original -tagsFromFile <source> -all:all <target>

        Parameters:
            source_path: Original video path
            target_path: Target video path
            tags: Specific tags only (None for all)
        """

    def apply_gps(
        self,
        source_path: Path,
        target_path: Path
    ) -> None:
        """
        Explicit GPS coordinate copy

        ExifTool command:
        exiftool -overwrite_original -tagsFromFile <source> "-GPS*" <target>
        """

    def sync_timestamps(
        self,
        source_path: Path,
        target_path: Path
    ) -> None:
        """
        Synchronize file system timestamps

        Uses os.utime()
        """
```

**GPS Tag Mapping**:
| ExifTool Tag | Description | Priority |
|--------------|-------------|----------|
| QuickTime:GPSCoordinates | QuickTime container GPS | 1 |
| Keys:GPSCoordinates | Apple Keys GPS | 2 |
| XMP:GPSLatitude | XMP GPS latitude | 3 |
| XMP:GPSLongitude | XMP GPS longitude | 3 |
| Composite:GPSLatitude | Calculated GPS latitude | 4 |
| Composite:GPSLongitude | Calculated GPS longitude | 4 |

---

### 3.5 Quality Management Module (SRS-500)

#### SRS-501: Conversion Result Verification

| Item | Content |
|------|---------|
| **ID** | SRS-501 |
| **Name** | Conversion Result Verification |
| **PRD Trace** | FR-301, FR-302, FR-303, US-503 |
| **Priority** | P0 (Required) |

**Description**:
Verify the integrity and quality of converted video files.

**Interface**:
```python
class QualityValidator:
    """Conversion quality validation"""

    def validate(
        self,
        original_path: Path,
        converted_path: Path,
        config: ValidationConfig
    ) -> ValidationResult:
        """
        Comprehensive conversion result validation

        Validation steps:
        1. File integrity check (FFprobe)
        2. Property comparison (resolution, framerate, duration)
        3. Compression ratio check (normal range verification)
        4. VMAF measurement (optional)
        """
```

**Validation Steps Detail**:

**Step 1: File Integrity Check**
```python
def check_integrity(self, path: Path) -> IntegrityResult:
    """
    File integrity check with FFprobe

    Command: ffprobe -v error -show_format -show_streams <path>

    Checks:
    - File exists and size > 0
    - Video stream exists
    - Codec info extractable
    - Duration > 0
    """
```

**Step 2: Property Comparison**
```python
def compare_properties(
    self,
    original: VideoProperties,
    converted: VideoProperties
) -> PropertyComparisonResult:
    """
    Video property comparison

    Comparison items and tolerances:
    - Resolution: Exact match
    - Frame rate: ±0.1 fps
    - Duration: ±1.0 second
    - Audio channels: Exact match
    """
```

**Step 3: Compression Ratio Check**
```python
def check_compression_ratio(
    self,
    original_size: int,
    converted_size: int
) -> CompressionResult:
    """
    Compression ratio normal range verification

    Normal range: 20% ~ 80%
    Warning range: 15-20% or 80-90%
    Error range: <15% or >90%

    Abnormal case analysis:
    - Too small: Possible quality loss
    - Too large: Conversion failure or inefficient encoding
    """
```

---

### 3.6 Automation Module (SRS-600)

#### SRS-601: Schedule-Based Execution

| Item | Content |
|------|---------|
| **ID** | SRS-601 |
| **Name** | Schedule-Based Auto Execution |
| **PRD Trace** | FR-401, US-401 |
| **Priority** | P0 (Required) |

**Description**:
Use launchd's StartCalendarInterval to automatically run conversion at specified times.

**plist Template**:
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
        <string>/usr/bin/python3</string>
        <string>${INSTALL_DIR}/main.py</string>
        <string>run</string>
        <string>--mode</string>
        <string>photos</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${SCHEDULE_HOUR}</integer>
        <key>Minute</key>
        <integer>${SCHEDULE_MINUTE}</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${LOG_DIR}/stdout.log</string>

    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/stderr.log</string>

    <key>ThrottleInterval</key>
    <integer>30</integer>
</dict>
</plist>
```

**Service Management Interface**:
```python
class LaunchdManager:
    """launchd service management"""

    PLIST_DIR = Path.home() / "Library/LaunchAgents"
    LABEL = "com.user.videoconverter"

    def install(self, config: AutomationConfig) -> None:
        """
        Install service

        1. Generate plist file
        2. Copy to LaunchAgents directory
        3. Execute launchctl load
        """

    def uninstall(self) -> None:
        """
        Remove service

        1. Execute launchctl unload
        2. Delete plist file
        """

    def start(self) -> None:
        """Manual service start: launchctl start <label>"""

    def stop(self) -> None:
        """Stop service: launchctl stop <label>"""

    def status(self) -> ServiceStatus:
        """Query service status: launchctl list | grep <label>"""
```

---

### 3.7 CLI Module (SRS-700)

#### SRS-701: CLI Command Structure

| Item | Content |
|------|---------|
| **ID** | SRS-701 |
| **Name** | CLI Command Structure |
| **PRD Trace** | FR-501 ~ FR-505 |
| **Priority** | P0 (Required) |

**Description**:
Access all system functions through command-line interface.

**Command Structure**:
```
video-converter <command> [options] [arguments]

Commands:
  convert       Single file conversion
  run           Batch conversion execution
  scan          Scan conversion targets (without converting)
  status        Service status check
  stats         Conversion statistics query
  config        Configuration management
  install       Service installation
  uninstall     Service removal
  version       Version information

Global Options:
  -c, --config PATH     Config file path
  -v, --verbose         Detailed log output
  -q, --quiet           Minimal output mode
  --log-file PATH       Log file path
  -h, --help            Show help
```

**Command Details**:

**convert command**:
```
video-converter convert <input> <output> [options]

Arguments:
  input                 Input video file path
  output                Output video file path

Options:
  -m, --mode MODE       Encoding mode (hardware|software) [default: hardware]
  -q, --quality INT     Quality setting (hardware: 1-100, software: CRF 0-51)
  --preset PRESET       Encoding preset (fast|medium|slow)
  --no-metadata         Don't copy metadata
  --validate            Validate quality after conversion

Examples:
  video-converter convert input.mp4 output.mp4
  video-converter convert input.mp4 output.mp4 -m hardware -q 45
  video-converter convert input.mp4 output.mp4 -m software --preset slow
```

**run command**:
```
video-converter run [options]

Options:
  --mode MODE           Source mode (photos|folder) [default: photos]
  --folder PATH         Target folder for folder mode
  --since DATE          Only videos after this date (YYYY-MM-DD)
  --album ALBUM         Specific albums only (can be specified multiple times)
  --dry-run             Simulate without actual conversion
  --limit N             Process maximum N items

Examples:
  video-converter run
  video-converter run --mode photos --since 2024-01-01
  video-converter run --mode folder --folder ~/Videos/ToConvert
  video-converter run --dry-run --limit 5
```

---

### 3.8 Safety Management Module (SRS-800)

#### SRS-801: Original Preservation

| Item | Content |
|------|---------|
| **ID** | SRS-801 |
| **Name** | Original File Preservation |
| **PRD Trace** | FR-601, US-501, US-502 |
| **Priority** | P0 (Required) |

**Description**:
On successful conversion, preserve original files by moving to a separate folder instead of deleting.

**Directory Structure**:
```
~/Videos/VideoConverter/
├── input/              # Conversion queue (folder mode)
├── output/             # Conversion results
├── processed/          # Successful originals (organized by date)
│   ├── 2024-12/
│   └── 2025-01/
├── failed/             # Failed originals
└── logs/               # Log files
```

---

## 4. Non-Functional Requirements Details

### 4.1 Performance Requirements (SRS-NFR-100)

| ID | Requirement | Target | Measurement | PRD Trace |
|----|-------------|--------|-------------|-----------|
| SRS-NFR-101 | 4K 30min video HW conversion | ≤5min | Benchmark | NFR-P01 |
| SRS-NFR-102 | 1080p 10min video HW conversion | ≤30sec | Benchmark | NFR-P02 |
| SRS-NFR-103 | CPU usage (HW mode) | ≤30% | Activity Monitor | NFR-P03 |
| SRS-NFR-104 | Memory usage | ≤1GB | Activity Monitor | NFR-P04 |
| SRS-NFR-105 | Codec detection time | ≤500ms | Unit test | - |
| SRS-NFR-106 | Photos scan (1000 items) | ≤30sec | Benchmark | - |

### 4.2 Reliability Requirements (SRS-NFR-200)

| ID | Requirement | Target | Measurement | PRD Trace |
|----|-------------|--------|-------------|-----------|
| SRS-NFR-201 | Conversion success rate | ≥99% | Batch test | NFR-R01 |
| SRS-NFR-202 | Metadata preservation rate | 100% | Auto verify | NFR-R02 |
| SRS-NFR-203 | Service uptime | ≥99.9% | Log analysis | NFR-R03 |
| SRS-NFR-204 | Error recovery success rate | ≥95% | Retry logs | NFR-R04 |

### 4.3 Compatibility Requirements (SRS-NFR-400)

| ID | Requirement | Target | Notes | PRD Trace |
|----|-------------|--------|-------|-----------|
| SRS-NFR-401 | macOS version | 12.0+ | Monterey or later | NFR-C01 |
| SRS-NFR-402 | Python version | 3.10+ | osxphotos requirement | NFR-C02 |
| SRS-NFR-403 | FFmpeg version | 5.0+ | hevc_videotoolbox | NFR-C03 |
| SRS-NFR-404 | ExifTool version | 12.0+ | GPS tag support | - |
| SRS-NFR-405 | osxphotos version | 0.70+ | Photos 16 support | - |
| SRS-NFR-406 | Video formats | .mp4/.mov/.m4v | H.264 codec | NFR-C04 |

### 4.4 Security Requirements (SRS-NFR-500)

| ID | Requirement | Implementation | PRD Trace |
|----|-------------|----------------|-----------|
| SRS-NFR-501 | Photos minimum privilege | Read-only access | NFR-S01 |
| SRS-NFR-502 | Temp file security | Delete immediately after use | NFR-S02 |
| SRS-NFR-503 | Config file security | 0600 permission | NFR-S03 |
| SRS-NFR-504 | Log privacy | Filename only, path hashed | - |
| SRS-NFR-505 | No external communication | Local processing only | - |

---

## 5. External Interface Requirements

### 5.1 User Interface

#### SRS-UI-001: CLI Interface

**Output Format**:

*Progress Display*:
```
Converting: vacation_2024.mp4
[████████████░░░░░░░░] 60% | 1.2GB → 540MB | ETA: 1:45
```

*Result Summary*:
```
╭─────────────────────────────────────────────╮
│           Conversion Report                  │
├─────────────────────────────────────────────┤
│  Videos processed:  15                       │
│  Success:           14                       │
│  Failed:            1                        │
│  Skipped:           3 (already HEVC)         │
├─────────────────────────────────────────────┤
│  Original size:     35.2 GB                  │
│  Converted size:    15.8 GB                  │
│  Space saved:       19.4 GB (55%)            │
╰─────────────────────────────────────────────╯
```

---

## 6. Data Requirements

### 6.1 Data Model

#### 6.1.1 Configuration Data

**config.json Schema** (abbreviated):
```json
{
  "version": "1.0.0",
  "encoding": {
    "mode": "hardware",
    "quality": 45,
    "crf": 22,
    "preset": "slow"
  },
  "paths": {
    "output": "~/Videos/Converted",
    "processed": "~/Videos/Processed",
    "failed": "~/Videos/Failed"
  },
  "automation": {
    "enabled": true,
    "schedule_hour": 3,
    "schedule_minute": 0
  }
}
```

#### 6.1.2 Conversion History Data

**SQLite Schema**:
```sql
CREATE TABLE conversion_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_uuid TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    original_path TEXT NOT NULL,
    output_path TEXT NOT NULL,
    original_size INTEGER NOT NULL,
    converted_size INTEGER NOT NULL,
    compression_ratio REAL NOT NULL,
    conversion_mode TEXT NOT NULL,
    quality_setting INTEGER,
    vmaf_score REAL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NOT NULL,
    duration_seconds REAL NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_video_uuid ON conversion_history(video_uuid);
CREATE INDEX idx_status ON conversion_history(status);
```

### 6.2 Data Storage

| Data Type | Location | Format |
|-----------|----------|--------|
| User config | ~/.config/video_converter/config.json | JSON |
| Conversion history | ~/.config/video_converter/history.db | SQLite |
| Execution logs | ~/Library/Logs/video_converter/ | Text |
| Temp files | /tmp/video_converter/ | Binary |

---

## 7. System Constraints

### 7.1 Technical Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| Cannot directly modify Photos library | Converted files stored separately | Clearly guide output folder |
| VideoToolbox quality limits | Slightly larger files than SW | Provide quality presets |
| iCloud sync delays | Some videos not processable | Retry logic, wait option |
| launchd ThrottleInterval | Minimum 30 second interval | Batch processing for efficiency |

### 7.2 Operational Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| Power required (laptop) | Battery drain | Check power state |
| 2x storage needed | Space shortage during conversion | Pre-check space |
| Mac must be powered on | Schedule may be missed | Process on next run |

---

## 8. Requirements Traceability Matrix (RTM)

### 8.1 PRD → SRS Tracing

| PRD ID | PRD Name | SRS ID | SRS Name | Status |
|--------|----------|--------|----------|--------|
| US-201 | Auto-find H.264 | SRS-101, SRS-301 | Codec detection, Photos scan | Mapped |
| US-203 | Progress check | SRS-201 | Progress monitoring | Mapped |
| US-301 | Date preservation | SRS-401, SRS-402 | Metadata processing | Mapped |
| US-302 | GPS preservation | SRS-401 | GPS special handling | Mapped |
| US-401 | Schedule execution | SRS-601 | launchd schedule | Mapped |
| FR-001 | H.264 detection | SRS-101 | Codec detection | Mapped |
| FR-002 | H.265 HW conversion | SRS-201 | Hardware conversion | Mapped |
| FR-003 | H.265 SW conversion | SRS-202 | Software conversion | Mapped |
| FR-101 | Photos scan | SRS-301 | Photos scan | Mapped |
| FR-201 | Metadata extraction | SRS-401 | Metadata extraction | Mapped |
| NFR-P01 | 4K conversion time | SRS-NFR-101 | ≤5min | Mapped |
| NFR-R01 | Conversion success rate | SRS-NFR-201 | ≥99% | Mapped |

---

## 9. Verification and Validation

### 9.1 Verification Methods

| Requirement Type | Verification Method | Tool |
|-----------------|---------------------|------|
| Functional requirements | Unit/Integration tests | pytest |
| Performance requirements | Benchmark tests | custom scripts |
| Reliability requirements | Long-run tests | CI/CD |
| Usability requirements | User testing | Survey/observation |

### 9.2 Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-001 | H.264 codec correctly detected | 10 samples 100% accurate |
| AC-002 | Converted file is HEVC codec | FFprobe verification |
| AC-003 | GPS coordinates match to 6 decimal places | ExifTool comparison |
| AC-004 | Date matches within 1 second | ExifTool comparison |
| AC-005 | Duration difference within 1 second | FFprobe comparison |

---

## 10. Appendix

### 10.1 Glossary

| Term | Definition |
|------|------------|
| H.264/AVC | Advanced Video Coding, video codec standardized in 2003 |
| H.265/HEVC | High Efficiency Video Coding, 50% improvement over H.264 |
| VideoToolbox | Apple hardware video encoding/decoding framework |
| CRF | Constant Rate Factor, quality-based encoding setting |
| VMAF | Video Multimethod Assessment Fusion, quality metric |
| launchd | macOS service management framework |
| osxphotos | Python Photos library access tool |
| ExifTool | Metadata read/write tool |
| FFmpeg | Multimedia processing framework |
| FFprobe | FFmpeg media analysis tool |

### 10.2 Error Code Definitions

| Code | Description | Retry | User Message |
|------|-------------|-------|--------------|
| E-101 | File not found | No | File not found |
| E-102 | FFprobe execution failed | Yes | Media analysis failed |
| E-103 | No video stream | No | File has no video |
| E-201 | FFmpeg execution failed | Yes | Conversion error |
| E-202 | Disk space insufficient | No | Not enough storage |
| E-203 | Input file corrupted | No | File is corrupted |
| E-301 | Photos access denied | No | Photos permission required |
| E-401 | Metadata extraction failed | Yes | Metadata read failed |

### 10.3 Reference Documents

- PRD.md - Product Requirements Document
- development-plan.md - Development Plan
- 01-system-architecture.md - System Architecture
- 02-sequence-diagrams.md - Sequence Diagrams
- 03-data-flow-and-states.md - Data Flow and States
- 04-processing-procedures.md - Processing Procedures

---

## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Tech Lead | | | |
| Architect | | | |
| QA Lead | | | |

---

*This document is updated as development progresses.*
