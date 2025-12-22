# Video Converter - Software Design Specification (SDS)

**Document Version**: 1.1.0
**Date**: 2025-12-23
**Status**: Active
**Reference Document**: SRS v1.0.0

---

## Document Information

### Traceability Information

| Item | Reference |
|------|-----------|
| Parent Document | SRS.md v1.0.0 |
| Related Documents | PRD.md, architecture/*.md, development-plan.md |
| Design ID Scheme | SDS-Mxx-xxx (Module-Item format) |

### Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-21 | - | Initial creation |
| 1.1.0 | 2025-12-23 | - | Updated directory structure to match implementation, added new modules (ui, vmaf_analyzer, concurrent, session, error_recovery, etc.) |

---

## Table of Contents

1. [Design Overview](#1-design-overview)
2. [System Architecture Design](#2-system-architecture-design)
3. [Module Detailed Design](#3-module-detailed-design)
4. [Class Detailed Design](#4-class-detailed-design)
5. [Database Design](#5-database-design)
6. [Interface Design](#6-interface-design)
7. [Error Handling Design](#7-error-handling-design)
8. [Security Design](#8-security-design)
9. [Performance Design](#9-performance-design)
10. [Design Traceability Matrix](#10-design-traceability-matrix)
11. [Appendix](#11-appendix)

---

## 1. Design Overview

### 1.1 Purpose

This document defines the detailed design of the Video Converter system. It provides specific design decisions, algorithms, data structures, and interfaces to implement the requirements specified in the SRS.

### 1.2 Scope

| Item | Content |
|------|---------|
| System Name | Video Converter |
| Target Version | v0.1.0.0+ |
| Design Scope | Entire system (Core modules, Automation, CLI) |

> **Note**: This project uses 0.x.x.x versioning to indicate active development status.

### 1.3 Design Principles

| Principle | Description | Application |
|-----------|-------------|-------------|
| **Single Responsibility (SRP)** | Each class has one responsibility | All class designs |
| **Open-Closed (OCP)** | Open for extension, closed for modification | Strategy pattern |
| **Dependency Inversion (DIP)** | Depend on abstractions, not concretions | Interface-based design |
| **Fail-Safe** | Prevent data loss on failure | Original preservation policy |
| **Progressive Processing** | Streaming for large data | Memory-efficient design |

### 1.4 Design ID Scheme

```
SDS-{Module}-{Number}
     │        │
     │        └── Sequence (001-999)
     └── Module Code:
         C01: Core (Orchestrator, Config)
         E01: Extractors
         V01: Video Converters
         P01: Processors (Codec, Metadata, Validator)
         A01: Automation (launchd, Folder Action)
         R01: Reporters (Statistics, Notifier)
         U01: Utils
         D01: Database
         I01: Interface (CLI)
```

---

## 2. System Architecture Design

### 2.1 Architecture Overview

> **Reference**: [01-system-architecture.md](architecture/01-system-architecture.md)

This system adopts a **4-Layer Architecture**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Presentation Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │     CLI     │  │   Notifier  │  │ Log Viewer  │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
├─────────────────────────────────────────────────────────────────────────┤
│                         Application Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │ Orchestrator│  │  Scheduler  │  │   Config    │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
├─────────────────────────────────────────────────────────────────────────┤
│                          Domain Layer                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Extractor  │  │  Converter  │  │  Metadata   │  │  Validator  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
├─────────────────────────────────────────────────────────────────────────┤
│                       Infrastructure Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ FFmpeg API  │  │ osxphotos   │  │  ExifTool   │  │   Logger    │    │
│  │  Adapter    │  │   Adapter   │  │   Adapter   │  │             │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Package Structure Design

| SDS ID | Package | Responsibility | SRS Trace |
|--------|---------|----------------|-----------|
| SDS-C01-001 | `video_converter.core` | Core orchestration, config management | SRS-701 |
| SDS-E01-001 | `video_converter.extractors` | Video source extraction | SRS-301, SRS-302 |
| SDS-V01-001 | `video_converter.converters` | Video encoding conversion | SRS-201, SRS-202 |
| SDS-P01-001 | `video_converter.processors` | Codec detection, metadata, validation | SRS-101, SRS-401, SRS-501 |
| SDS-A01-001 | `video_converter.automation` | launchd automation management | SRS-601, SRS-602 |
| SDS-R01-001 | `video_converter.reporters` | Statistics and notifications | SRS-603 |
| SDS-U01-001 | `video_converter.utils` | Common utilities | - |

### 2.3 Directory Structure

```
video_converter/
├── src/
│   └── video_converter/
│       ├── __init__.py
│       ├── __main__.py                # CLI Entry point
│       ├── core/
│       │   ├── __init__.py
│       │   ├── orchestrator.py        # SDS-C01-001 (Main workflow coordinator)
│       │   ├── config.py              # SDS-C01-002 (Configuration management)
│       │   ├── logger.py              # SDS-C01-003 (Logging system)
│       │   ├── types.py               # SDS-C01-004 (Core data classes)
│       │   ├── session.py             # SDS-C01-005 (Session persistence)
│       │   ├── history.py             # SDS-C01-006 (Conversion history)
│       │   ├── error_recovery.py      # SDS-C01-007 (Error handling)
│       │   └── concurrent.py          # SDS-C01-008 (Parallel processing)
│       ├── extractors/
│       │   ├── __init__.py
│       │   ├── photos_extractor.py    # SDS-E01-001 (Photos library access)
│       │   ├── folder_extractor.py    # SDS-E01-002 (Filesystem scanning)
│       │   └── icloud_handler.py      # SDS-E01-003 (iCloud file handling)
│       ├── importers/
│       │   ├── __init__.py
│       │   ├── photos_importer.py         # SDS-P01-009 (Photos re-import)
│       │   └── metadata_preservation.py   # SDS-P01-010 (Metadata preservation)
│       ├── converters/
│       │   ├── __init__.py
│       │   ├── base.py                # SDS-V01-001 (Abstract interface)
│       │   ├── hardware.py            # SDS-V01-002 (VideoToolbox encoder)
│       │   ├── software.py            # SDS-V01-003 (libx265 encoder)
│       │   ├── factory.py             # SDS-V01-004 (Converter factory)
│       │   └── progress.py            # SDS-V01-005 (FFmpeg progress parsing)
│       ├── processors/
│       │   ├── __init__.py
│       │   ├── codec_detector.py      # SDS-P01-001 (Codec detection)
│       │   ├── metadata.py            # SDS-P01-002 (ExifTool metadata)
│       │   ├── quality_validator.py   # SDS-P01-003 (Quality validation)
│       │   ├── gps.py                 # SDS-P01-004 (GPS coordinates)
│       │   ├── vmaf_analyzer.py       # SDS-P01-005 (VMAF analysis)
│       │   ├── verification.py        # SDS-P01-006 (Output verification)
│       │   ├── timestamp.py           # SDS-P01-007 (File timestamps)
│       │   └── retry_manager.py       # SDS-P01-008 (Retry logic)
│       ├── automation/
│       │   ├── __init__.py
│       │   ├── service_manager.py     # SDS-A01-001 (launchd service)
│       │   ├── launchd.py             # SDS-A01-002 (plist generation)
│       │   └── notification.py        # SDS-A01-003 (macOS notifications)
│       ├── reporters/
│       │   ├── __init__.py
│       │   ├── statistics_reporter.py # SDS-R01-001 (Stats formatting)
│       │   └── batch_reporter.py      # SDS-R01-002 (Batch reporting)
│       ├── ui/
│       │   ├── __init__.py
│       │   └── progress.py            # SDS-UI-001 (Rich progress display)
│       └── utils/
│           ├── __init__.py
│           ├── command_runner.py      # SDS-U01-001 (External tool execution)
│           ├── progress_parser.py     # SDS-U01-002 (FFmpeg output parsing)
│           ├── file_utils.py          # SDS-U01-003 (File operations)
│           ├── dependency_checker.py  # SDS-U01-004 (System dependency check)
│           └── applescript.py         # SDS-U01-005 (AppleScript execution)
├── tests/
│   ├── unit/                          # Unit tests (31 files)
│   ├── integration/                   # Integration tests
│   └── conftest.py                    # Pytest fixtures
├── config/
│   ├── default.json                   # Default configuration
│   └── launchd/                       # Service templates
└── scripts/
    ├── install.sh
    └── uninstall.sh
```

---

## 3. Module Detailed Design

### 3.1 Core Module (SDS-C01)

#### SDS-C01-001: Orchestrator Design

| Item | Content |
|------|---------|
| **SDS ID** | SDS-C01-001 |
| **Module** | Orchestrator |
| **File** | `src/video_converter/core/orchestrator.py` |
| **SRS Trace** | SRS-701 (CLI Command Structure) |
| **Responsibility** | Coordinate entire conversion workflow and manage state |

**Class Design**:

```python
class Orchestrator:
    """
    Main workflow orchestrator

    Attributes:
        config: Config - System configuration
        extractor: VideoExtractor - Video extractor
        converter: VideoConverter - Video converter
        validator: QualityValidator - Quality validator
        metadata_manager: MetadataManager - Metadata manager
        reporter: StatisticsReporter - Statistics reporter
        notifier: MacOSNotifier - Notification manager
        history: ConversionHistory - Conversion history manager
        _session: ConversionSession - Current session info

    Design Patterns:
        - Facade: Provide simplified interface to complex subsystems
        - Template Method: Define conversion workflow skeleton
    """

    def __init__(self, config: Config):
        """Initialize with configuration"""
        pass

    async def run_batch(
        self,
        mode: str = "photos",
        options: BatchOptions = None
    ) -> BatchResult:
        """
        Execute batch conversion

        Algorithm:
        1. Create new session
        2. Scan conversion targets
        3. Filter already converted
        4. Process each video:
           a. Export (if Photos mode)
           b. Convert
           c. Validate
           d. Apply metadata
           e. Cleanup
        5. Generate report
        6. Send notification
        """
        pass

    async def convert_single(
        self,
        input_path: Path,
        output_path: Path,
        options: ConversionOptions = None
    ) -> ConversionResult:
        """
        Convert single file

        Steps:
        1. Detect codec
        2. Execute conversion
        3. Validate result
        4. Apply metadata
        5. Return result
        """
        pass
```

#### SDS-C01-002: Configuration Design

| Item | Content |
|------|---------|
| **SDS ID** | SDS-C01-002 |
| **Module** | Config |
| **File** | `src/video_converter/core/config.py` |
| **SRS Trace** | SRS-UI-001 |
| **Responsibility** | Configuration management and validation |

**Configuration Hierarchy**:

```
Priority (high to low):
1. CLI Arguments
2. Environment Variables
3. User Config (~/.config/video_converter/config.json)
4. Default Config (built-in)
```

#### SDS-C01-003: Logger Design

| Item | Content |
|------|---------|
| **SDS ID** | SDS-C01-003 |
| **Module** | Logger |
| **File** | `src/video_converter/core/logger.py` |
| **SRS Trace** | SRS-101 (Logging System) |
| **Responsibility** | Comprehensive logging with file and console output |
| **Status** | ✅ Implemented |

**Logger Architecture**:

```python
class LogLevel:
    """Log level constants."""
    DEBUG = logging.DEBUG      # Detailed debugging information
    INFO = logging.INFO        # General operational information
    WARNING = logging.WARNING  # Potential issues
    ERROR = logging.ERROR      # Error that prevented operation
    CRITICAL = logging.CRITICAL # Critical error

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    pass

def configure_logging(
    level: int | str = DEFAULT_LOG_LEVEL,
    log_dir: Path | None = None,
    console_output: bool = True,
    file_output: bool = True,
) -> None:
    """Configure global logging settings."""
    pass
```

**Key Features**:

| Feature | Implementation |
|---------|----------------|
| File Output | RotatingFileHandler (10MB, 5 backups) |
| Console Output | Rich library with colored output |
| Log Format | `[%(asctime)s] %(levelname)-8s \| %(name)s \| %(message)s` |
| Log Directory | `~/.local/share/video_converter/logs/` |
| Rotation | Automatic rotation at 10MB with 5 backup files |

---

### 3.2 Converters Module (SDS-V01)

#### SDS-V01-002: Hardware Converter Design

| Item | Content |
|------|---------|
| **SDS ID** | SDS-V01-002 |
| **Module** | HardwareConverter |
| **File** | `src/video_converter/converters/hardware.py` |
| **SRS Trace** | SRS-201, SRS-205 |
| **Responsibility** | VideoToolbox hardware-accelerated H.265 encoding with real-time progress |
| **Status** | ✅ Implemented |

**Conversion Algorithm**:

```python
class HardwareConverter(BaseConverter):
    """
    VideoToolbox hardware accelerated converter

    Uses Apple Silicon Media Engine for fast H.265 encoding.
    Typically 20x+ realtime for 4K content.

    Features:
    - Real-time progress tracking via FFmpeg stderr parsing
    - Speed ratio calculation (actual vs video duration)
    - Metadata preservation with use_metadata_tags movflag
    """

    def build_command(self, request: ConversionRequest) -> List[str]:
        """
        Build FFmpeg command for hardware encoding

        Command Template:
        ffmpeg -y -i <input>
            -c:v hevc_videotoolbox
            -q:v <quality>
            -tag:v hvc1
            -c:a copy
            -map_metadata 0
            -movflags +faststart+use_metadata_tags
            <output>
        """
        return [
            "ffmpeg", "-y",
            "-i", str(request.input_path),
            "-c:v", "hevc_videotoolbox",
            "-q:v", str(request.quality),
            "-tag:v", "hvc1",
            "-c:a", "copy",
            "-map_metadata", "0",
            "-movflags", "+faststart+use_metadata_tags",
            str(request.output_path)
        ]
```

**Progress Tracking**:

The base converter parses FFmpeg stderr output in real-time to extract:
- Frame count and FPS
- Current time position
- Encoding speed (e.g., 6.0x realtime)
- Bitrate and output size

Progress percentage is calculated as: `current_time / total_duration * 100`

Speed ratio is derived from FFmpeg's reported speed or calculated from actual conversion time.

---

### 3.3 Processors Module (SDS-P01)

#### SDS-P01-001: Codec Detector Design

| Item | Content |
|------|---------|
| **SDS ID** | SDS-P01-001 |
| **Module** | CodecDetector |
| **File** | `src/video_converter/processors/codec_detector.py` |
| **SRS Trace** | SRS-101 |
| **Responsibility** | Video codec detection and classification |
| **Status** | ✅ Implemented |

**Detection Algorithm**:

```python
class CodecDetector:
    """
    Video codec detector using FFprobe.

    Uses FFprobeRunner to analyze video files and extract:
    - Video codec (h264, hevc, vp9, etc.)
    - Resolution and frame rate
    - Duration and bitrate
    - Audio codec and container format
    - Creation timestamp
    """

    def analyze(self, path: Path) -> CodecInfo:
        """
        Analyze video file and return codec information.

        FFprobe Command:
        ffprobe -v error -print_format json
                -show_format -show_streams <path>

        Returns:
            CodecInfo with is_h264, is_hevc, needs_conversion properties
        """

@dataclass
class CodecInfo:
    """Video codec and property information."""
    path: Path
    codec: str           # "h264", "hevc", "vp9", etc.
    width: int           # Video width in pixels
    height: int          # Video height in pixels
    fps: float           # Frames per second
    duration: float      # Duration in seconds
    bitrate: int         # Bitrate in bits/second
    size: int            # File size in bytes
    audio_codec: str     # "aac", "opus", etc.
    container: str       # "mp4", "mov", "mkv"
    creation_time: datetime | None

    H264_CODECS = frozenset({"h264", "avc", "avc1", "x264"})
    HEVC_CODECS = frozenset({"hevc", "h265", "hvc1", "hev1", "x265"})

    @property
    def is_h264(self) -> bool: ...

    @property
    def is_hevc(self) -> bool: ...

    @property
    def needs_conversion(self) -> bool: ...

    @property
    def resolution_label(self) -> str:
        """Returns "4K", "1080p", "720p", etc."""
```

**Error Classes**:

| Exception | Description |
|-----------|-------------|
| `InvalidVideoError` | File is not a valid video |
| `CorruptedVideoError` | Video file is corrupted/incomplete |
| `UnsupportedCodecError` | Unknown or unsupported codec |

#### SDS-P01-002: Metadata Manager Design

| Item | Content |
|------|---------|
| **SDS ID** | SDS-P01-002 |
| **Module** | MetadataManager |
| **File** | `src/video_converter/processors/metadata_manager.py` |
| **SRS Trace** | SRS-401, SRS-402 |
| **Responsibility** | Metadata extraction, application, and verification |

**GPS Preservation Algorithm**:

```python
class MetadataManager:
    """
    Metadata management using ExifTool

    GPS Tag Priority:
    1. QuickTime:GPSCoordinates
    2. Keys:GPSCoordinates
    3. XMP:GPSLatitude/Longitude
    4. Composite:GPSLatitude/Longitude
    """

    async def apply_all(self, source: Path, target: Path) -> None:
        """
        Apply all metadata from source to target

        Steps:
        1. Copy all tags: exiftool -tagsFromFile <src> -all:all <dst>
        2. Explicit GPS copy: exiftool -tagsFromFile <src> "-GPS*" <dst>
        3. Sync timestamps: os.utime()
        """
        pass

    def verify_gps(self, original: Metadata, converted: Metadata) -> bool:
        """
        Verify GPS preservation

        Tolerance: 6 decimal places (~0.1m)
        """
        pass
```

#### SDS-P01-004: GPS Handler Design

| Item | Content |
|------|---------|
| **SDS ID** | SDS-P01-004 |
| **Module** | GPSHandler |
| **File** | `src/video_converter/processors/gps.py` |
| **SRS Trace** | SRS-402 (GPS Preservation) |
| **Responsibility** | GPS coordinate extraction, application, format conversion, and verification |

**GPS Coordinate Formats**:

| Format | Example | Container |
|--------|---------|-----------|
| QuickTime (ISO 6709) | `+37.774900-122.419400/` | QuickTime, Keys |
| XMP | `37.774900 N`, `122.419400 W` | XMP metadata |
| EXIF DMS | `37 deg 46' 30.00"` | EXIF |
| Decimal | `37.7749`, `-122.4194` | Composite |

**Design**:

```python
@dataclass
class GPSCoordinates:
    """GPS coordinate with format conversion support."""
    latitude: float       # -90 to 90
    longitude: float      # -180 to 180
    altitude: float | None = None
    accuracy: float | None = None
    source_format: GPSFormat = GPSFormat.DECIMAL

    PRECISION = 6         # ~0.1m accuracy
    TOLERANCE = 0.000001  # Verification tolerance

    def to_quicktime(self) -> str:
        """Convert to ISO 6709 format: +37.774900-122.419400/"""
        pass

    def to_xmp(self) -> tuple[str, str]:
        """Convert to XMP format: ('37.774900 N', '122.419400 W')"""
        pass

    def to_exif_dms(self) -> tuple[str, str, str, str]:
        """Convert to EXIF DMS format."""
        pass

    def matches(self, other: GPSCoordinates, tolerance: float | None = None) -> bool:
        """Compare coordinates within tolerance."""
        pass

    def distance_to(self, other: GPSCoordinates) -> float:
        """Calculate distance in meters using Haversine formula."""
        pass

class GPSHandler:
    """Handle GPS coordinate preservation during video conversion."""

    def extract(self, path: Path) -> GPSCoordinates | None:
        """Extract GPS from video, checking all format locations."""
        pass

    def apply(self, path: Path, coords: GPSCoordinates) -> bool:
        """Apply GPS coordinates in multiple formats."""
        pass

    def copy(self, source: Path, dest: Path) -> bool:
        """Copy GPS data from source to destination."""
        pass

    def verify(self, original: Path, converted: Path) -> GPSVerificationResult:
        """Verify GPS was preserved within tolerance."""
        pass
```

#### SDS-P01-005: Photos Video Filter Design

| Item | Content |
|------|---------|
| **SDS ID** | SDS-P01-005 |
| **Module** | PhotosVideoFilter |
| **File** | `src/video_converter/extractors/photos_extractor.py` |
| **SRS Trace** | SRS-302 (Video Filtering) |
| **Responsibility** | Filter Photos library videos for H.264 conversion candidates |

**Filter Criteria**:

| Criterion | Include | Exclude |
|-----------|---------|---------|
| Codec | H.264, AVC, AVC1, x264 | HEVC, H.265, hvc1, hev1, x265, VP9, AV1 |
| Albums | User-specified | Screenshots, Bursts, Slo-mo (default) |
| Availability | Local files only | iCloud-only files |
| Validity | Valid video files | Corrupted or invalid files |

**Design**:

```python
@dataclass
class LibraryStats:
    """Statistics about videos in the Photos library."""
    total: int = 0
    h264: int = 0
    hevc: int = 0
    other: int = 0
    in_cloud: int = 0
    total_size_h264: int = 0

    @property
    def estimated_savings(self) -> int:
        """Estimate ~50% savings with H.265 conversion."""
        return int(self.total_size_h264 * 0.5)

class PhotosVideoFilter:
    """Filter Photos library videos for conversion candidates."""

    DEFAULT_EXCLUDE_ALBUMS = {"Screenshots", "Bursts", "Slo-mo"}

    def __init__(
        self,
        library: PhotosLibrary,
        include_albums: list[str] | None = None,
        exclude_albums: list[str] | None = None,
    ) -> None:
        """Initialize filter with album configuration."""
        pass

    def get_conversion_candidates(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[PhotosVideoInfo]:
        """Get H.264 videos that need conversion."""
        pass

    def get_stats(self) -> LibraryStats:
        """Get library statistics with codec distribution."""
        pass
```

#### SDS-P01-006: Video Exporter Design

| Item | Content |
|------|---------|
| **SDS ID** | SDS-P01-006 |
| **Module** | VideoExporter |
| **File** | `src/video_converter/extractors/photos_extractor.py` |
| **SRS Trace** | SRS-303 (Video Export) |
| **Responsibility** | Export videos from Photos library to temporary directory for conversion |

**Features**:

| Feature | Description |
|---------|-------------|
| Progress Tracking | Callback support for large file copy progress (0.0-1.0) |
| Metadata Preservation | Copies file with preserved modification times |
| Safe Cleanup | Only removes files within managed temp directory |
| Context Manager | Automatic cleanup on exit with `with` statement |
| iCloud Handling | Raises `VideoNotAvailableError` for cloud-only videos |

**Design**:

```python
class VideoExporter:
    """Export videos from Photos library to temporary directory."""

    COPY_BUFFER_SIZE = 1024 * 1024  # 1 MB

    def __init__(self, temp_dir: Path | None = None) -> None:
        """Initialize with optional custom temp directory."""
        pass

    def export(
        self,
        video: PhotosVideoInfo,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        """Export video to temporary directory with progress tracking."""
        pass

    def cleanup(self, path: Path) -> bool:
        """Remove a single exported file (within temp_dir only)."""
        pass

    def cleanup_all(self) -> int:
        """Remove all exported files and temp directory if owned."""
        pass
```

**Error Classes**:

| Exception | Description |
|-----------|-------------|
| `VideoNotAvailableError` | Raised when video is iCloud-only and not downloaded |
| `ExportError` | Raised when export fails (permission denied, disk full, etc.) |

#### SDS-P01-009: Photos Importer Design

| Item | Content |
|------|---------|
| **SDS ID** | SDS-P01-009 |
| **Module** | PhotosImporter |
| **File** | `src/video_converter/importers/photos_importer.py` |
| **SRS Trace** | SRS-305 (Photos Re-Import) |
| **Responsibility** | Import converted videos back to Photos library with AppleScript |

**Features**:

| Feature | Description |
|---------|-------------|
| Video Import | Import video files to Photos library via AppleScript |
| UUID Return | Returns Photos library UUID for imported video |
| Import Verification | Verify successful import by checking UUID existence |
| Timeout Handling | Configurable timeout (default 5 minutes) for large videos |
| Error Classification | Specific exceptions for different failure modes |

**Design**:

```python
class PhotosImporter:
    """Import videos to macOS Photos library via AppleScript."""

    DEFAULT_TIMEOUT = 300.0  # 5 minutes

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Initialize with configurable timeout."""
        pass

    def import_video(self, video_path: Path) -> str:
        """Import video to Photos library and return UUID."""
        pass

    def verify_import(self, uuid: str) -> bool:
        """Verify that import was successful by UUID."""
        pass

    def get_video_info(self, uuid: str) -> dict[str, str] | None:
        """Get information about an imported video."""
        pass
```

**Error Classes**:

| Exception | Description |
|-----------|-------------|
| `PhotosImportError` | Base exception for all import operations |
| `PhotosNotRunningError` | Raised when Photos.app cannot be activated |
| `ImportTimeoutError` | Raised when import operation exceeds timeout |
| `DuplicateVideoError` | Raised when video already exists in library |
| `ImportFailedError` | Raised when import fails for other reasons |

**AppleScript Utility** (`src/video_converter/utils/applescript.py`):

| Class | Description |
|-------|-------------|
| `AppleScriptRunner` | Execute AppleScript commands via osascript |
| `AppleScriptResult` | Result dataclass with returncode, stdout, stderr |
| `AppleScriptError` | Base exception for AppleScript errors |
| `AppleScriptTimeoutError` | Execution timeout exception |
| `AppleScriptExecutionError` | Script execution failure exception |

---

## 4. Class Detailed Design

### 4.1 Data Classes

```python
@dataclass
class VideoInfo:
    """Video information"""
    uuid: str
    original_filename: str
    path: Optional[Path]
    codec: str
    duration: float
    size: int
    width: int
    height: int
    fps: float
    creation_date: datetime
    location: Optional[Tuple[float, float]]
    albums: List[str]
    is_in_icloud: bool

@dataclass
class ConversionRequest:
    """Conversion request parameters"""
    input_path: Path
    output_path: Path
    mode: str = "hardware"
    quality: int = 45
    crf: int = 22
    preset: str = "medium"
    audio_mode: str = "copy"

@dataclass
class ConversionResult:
    """Conversion result"""
    success: bool
    input_path: Path
    output_path: Path
    original_size: int
    converted_size: int
    compression_ratio: float
    duration_seconds: float
    speed_ratio: float
    error_message: Optional[str] = None

@dataclass
class ValidationResult:
    """Validation result"""
    valid: bool
    integrity_ok: bool
    properties_match: bool
    compression_normal: bool
    vmaf_score: Optional[float]
    errors: List[str]
    warnings: List[str]
```

---

## 5. Database Design

### 5.1 SQLite Schema

```sql
-- Conversion History Table
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

-- Indexes
CREATE INDEX idx_video_uuid ON conversion_history(video_uuid);
CREATE INDEX idx_status ON conversion_history(status);
CREATE INDEX idx_completed_at ON conversion_history(completed_at);

-- Session Table
CREATE TABLE conversion_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_uuid TEXT NOT NULL UNIQUE,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_videos INTEGER NOT NULL,
    successful INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    skipped INTEGER DEFAULT 0,
    total_original_size INTEGER DEFAULT 0,
    total_converted_size INTEGER DEFAULT 0,
    status TEXT NOT NULL
);
```

---

## 6. Interface Design

### 6.1 CLI Interface Design

**Command Structure**:

```
video-converter <command> [options] [arguments]

Commands:
  convert     Single file conversion
  run         Batch conversion
  scan        Scan targets (no conversion)
  status      Service status
  stats       Statistics query
  config      Configuration management
  install     Install service
  uninstall   Remove service
```

**Output Formats**:

Progress:
```
Converting: vacation_2024.mp4
[████████████░░░░░░░░] 60% | 1.2GB → 540MB | ETA: 1:45
```

Report:
```
╭─────────────────────────────────────────────╮
│           Conversion Report                  │
├─────────────────────────────────────────────┤
│  Videos processed:  15                       │
│  Success:           14                       │
│  Failed:            1                        │
│  Skipped:           3                        │
├─────────────────────────────────────────────┤
│  Original size:     35.2 GB                  │
│  Converted size:    15.8 GB                  │
│  Space saved:       19.4 GB (55%)            │
╰─────────────────────────────────────────────╯
```

---

## 7. Error Handling Design

### 7.1 Exception Hierarchy

```python
class VideoConverterError(Exception):
    """Base exception"""
    pass

class FileError(VideoConverterError):
    """File-related errors"""
    pass

class FileNotFoundError(FileError):
    """File not found (E-101)"""
    pass

class ConversionError(VideoConverterError):
    """Conversion-related errors"""
    pass

class FFmpegError(ConversionError):
    """FFmpeg execution error (E-201)"""
    pass

class MetadataError(VideoConverterError):
    """Metadata-related errors"""
    pass

class ValidationError(VideoConverterError):
    """Validation-related errors"""
    pass
```

### 7.2 Retry Policy

```python
@dataclass
class RetryPolicy:
    """Retry policy configuration"""
    max_retries: int = 3
    base_delay: float = 5.0
    max_delay: float = 60.0
    exponential_base: float = 2.0

    def get_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff"""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
```

---

## 8. Security Design

### 8.1 Access Control

| Resource | Permission | Implementation |
|----------|------------|----------------|
| Photos Library | Read-only | osxphotos read-only access |
| Config Files | User only | 0600 permission |
| Log Files | User only | 0600 permission |
| Temp Files | Secure delete | Immediate cleanup after use |

### 8.2 Data Protection

- **No network communication**: All processing is local
- **Path hashing in logs**: File paths are hashed, not stored in plain text
- **Secure temp files**: Located in /tmp with automatic cleanup

---

## 9. Performance Design

### 9.1 Performance Targets

| Metric | Target | Design Approach |
|--------|--------|-----------------|
| 4K 30min HW conversion | ≤5min | VideoToolbox hardware acceleration |
| CPU usage (HW mode) | ≤30% | Offload to Media Engine |
| Memory usage | ≤1GB | Streaming processing |
| Concurrent conversions | 2 | Configurable parallelism |

### 9.2 Optimization Strategies

1. **Hardware Acceleration**: Use VideoToolbox for all compatible content
2. **Streaming Processing**: Process large files without full memory load
3. **Parallel Processing**: Convert multiple files concurrently
4. **Early Filtering**: Skip already-converted files before export

---

## 10. Design Traceability Matrix

### 10.1 SRS → SDS Tracing

| SRS ID | SRS Name | SDS ID | SDS Name | Status |
|--------|----------|--------|----------|--------|
| SRS-101 | Codec Detection | SDS-P01-001 | CodecDetector | Mapped |
| SRS-201 | HW Conversion | SDS-V01-002 | HardwareConverter | Mapped |
| SRS-202 | SW Conversion | SDS-V01-003 | SoftwareConverter | Mapped |
| SRS-205 | Progress Monitoring | SDS-U01-002 | FFmpegProgressParser | Mapped |
| SRS-301 | Photos Scan | SDS-E01-002 | PhotosExtractor | Mapped |
| SRS-302 | Video Filtering | SDS-P01-005 | PhotosVideoFilter | Mapped |
| SRS-303 | Video Export | SDS-P01-006 | VideoExporter | Mapped |
| SRS-305 | Photos Re-Import | SDS-P01-009 | PhotosImporter | Mapped |
| SRS-401 | Metadata Extraction | SDS-P01-002 | MetadataManager | Mapped |
| SRS-402 | GPS Preservation | SDS-P01-004 | GPSHandler | Mapped |
| SRS-501 | Quality Validation | SDS-P01-003 | QualityValidator | Mapped |
| SRS-601 | Schedule Execution | SDS-A01-001 | LaunchdManager | Mapped |
| SRS-701 | CLI Structure | SDS-I01-001 | CLI | Mapped |

### 10.2 SDS → Code Tracing

| SDS ID | File | Class/Function |
|--------|------|----------------|
| **Core Module** |
| SDS-C01-001 | orchestrator.py | Orchestrator |
| SDS-C01-002 | config.py | Config |
| SDS-C01-003 | logger.py | get_logger, configure_logging |
| SDS-C01-004 | types.py | ConversionRequest, ConversionResult, ConversionProgress |
| SDS-C01-005 | session.py | ConversionSession |
| SDS-C01-006 | history.py | ConversionHistory, ConversionRecord |
| SDS-C01-007 | error_recovery.py | ErrorRecoveryManager, ErrorCategory |
| SDS-C01-008 | concurrent.py | ConcurrentProcessor, ResourceMonitor |
| **Extractors Module** |
| SDS-E01-001 | photos_extractor.py | PhotosExtractor |
| SDS-E01-002 | folder_extractor.py | FolderExtractor, FolderVideoInfo |
| SDS-E01-003 | icloud_handler.py | iCloudHandler, CloudStatus |
| **Converters Module** |
| SDS-V01-001 | base.py | BaseConverter |
| SDS-V01-002 | hardware.py | HardwareConverter |
| SDS-V01-003 | software.py | SoftwareConverter |
| SDS-V01-004 | factory.py | ConverterFactory |
| SDS-V01-005 | progress.py | ProgressInfo, ProgressParser |
| **Processors Module** |
| SDS-P01-001 | codec_detector.py | CodecDetector, CodecInfo |
| SDS-P01-002 | metadata.py | MetadataProcessor |
| SDS-P01-003 | quality_validator.py | QualityValidator |
| SDS-P01-004 | gps.py | GPSHandler, GPSCoordinates |
| SDS-P01-005 | vmaf_analyzer.py | VmafAnalyzer, VmafScores |
| SDS-P01-006 | verification.py | OutputVerifier |
| SDS-P01-007 | timestamp.py | TimestampSynchronizer |
| SDS-P01-008 | retry_manager.py | RetryManager, RetryConfig |
| **Automation Module** |
| SDS-A01-001 | service_manager.py | ServiceManager |
| SDS-A01-002 | launchd.py | LaunchdGenerator |
| SDS-A01-003 | notification.py | NotificationManager |
| **Reporters Module** |
| SDS-R01-001 | statistics_reporter.py | StatisticsReporter |
| SDS-R01-002 | batch_reporter.py | BatchReporter |
| **UI Module** |
| SDS-UI-001 | ui/progress.py | SingleFileProgressDisplay, BatchProgressDisplay |
| **Utils Module** |
| SDS-U01-001 | command_runner.py | CommandRunner, FFprobeRunner |
| SDS-U01-002 | progress_parser.py | FFmpegProgressParser |
| SDS-U01-003 | file_utils.py | FileUtils |
| SDS-U01-004 | dependency_checker.py | DependencyChecker |
| SDS-U01-005 | applescript.py | AppleScriptRunner |
| **Importers Module** |
| SDS-P01-009 | photos_importer.py | PhotosImporter |

---

## 11. Appendix

### 11.1 Design Patterns Used

| Pattern | Application | Location |
|---------|-------------|----------|
| Strategy | Converter selection (HW/SW) | converters/ |
| Factory | Extractor creation | extractors/ |
| Facade | Orchestrator | core/orchestrator.py |
| Template Method | Conversion workflow | converters/base.py |
| Adapter | External tool integration | adapters/ |
| Observer | Progress monitoring | utils/progress_parser.py, converters/base.py |

### 11.2 Reference Documents

- PRD.md - Product Requirements Document
- SRS.md - Software Requirements Specification
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
| Lead Developer | | | |

---

*This document is updated as development progresses.*
