# Video Converter - Software Design Specification (SDS)

**Document Version**: 1.0.0
**Date**: 2025-12-21
**Status**: Draft
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
| Target Version | v1.0.0 |
| Design Scope | Entire system (Core modules, Automation, CLI) |

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
│       ├── main.py                    # Entry point
│       ├── core/
│       │   ├── __init__.py
│       │   ├── orchestrator.py        # SDS-C01-001
│       │   └── config.py              # SDS-C01-002
│       ├── extractors/
│       │   ├── __init__.py
│       │   ├── base.py                # SDS-E01-001
│       │   ├── photos_extractor.py    # SDS-E01-002
│       │   └── folder_extractor.py    # SDS-E01-003
│       ├── converters/
│       │   ├── __init__.py
│       │   ├── base.py                # SDS-V01-001
│       │   ├── hardware_converter.py  # SDS-V01-002
│       │   └── software_converter.py  # SDS-V01-003
│       ├── processors/
│       │   ├── __init__.py
│       │   ├── codec_detector.py      # SDS-P01-001
│       │   ├── metadata_manager.py    # SDS-P01-002
│       │   └── quality_validator.py   # SDS-P01-003
│       ├── automation/
│       │   ├── __init__.py
│       │   ├── launchd_manager.py     # SDS-A01-001
│       │   └── folder_watcher.py      # SDS-A01-002
│       ├── reporters/
│       │   ├── __init__.py
│       │   ├── statistics.py          # SDS-R01-001
│       │   └── notifier.py            # SDS-R01-002
│       └── utils/
│           ├── __init__.py
│           ├── command_runner.py      # SDS-U01-001
│           ├── file_utils.py          # SDS-U01-002
│           └── logging.py             # SDS-U01-003
├── tests/
├── config/
│   └── defaults.json
└── scripts/
    └── install.sh
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

---

### 3.2 Converters Module (SDS-V01)

#### SDS-V01-002: Hardware Converter Design

| Item | Content |
|------|---------|
| **SDS ID** | SDS-V01-002 |
| **Module** | HardwareConverter |
| **File** | `src/video_converter/converters/hardware_converter.py` |
| **SRS Trace** | SRS-201 |
| **Responsibility** | VideoToolbox hardware-accelerated H.265 encoding |

**Conversion Algorithm**:

```python
class HardwareConverter(BaseConverter):
    """
    VideoToolbox hardware accelerated converter

    Uses Apple Silicon Media Engine for fast H.265 encoding.
    Typically 20x+ realtime for 4K content.
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
            -movflags use_metadata_tags
            -progress pipe:1
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
            "-movflags", "use_metadata_tags",
            "-progress", "pipe:1",
            str(request.output_path)
        ]
```

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

**Detection Algorithm**:

```python
class CodecDetector:
    """
    Video codec detector using FFprobe

    Codec Mapping:
    - h264, avc, avc1 → H.264
    - hevc, h265, hvc1, hev1 → HEVC
    """

    CODEC_MAPPING = {
        "h264": "h264", "avc": "h264", "avc1": "h264",
        "hevc": "hevc", "h265": "hevc", "hvc1": "hevc", "hev1": "hevc"
    }

    async def detect(self, video_path: Path) -> CodecInfo:
        """
        Detect video codec

        FFprobe Command:
        ffprobe -v error -select_streams v:0
                -show_entries stream=codec_name
                -of default=noprint_wrappers=1:nokey=1
                <path>
        """
        pass
```

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
| SRS-301 | Photos Scan | SDS-E01-002 | PhotosExtractor | Mapped |
| SRS-401 | Metadata Extraction | SDS-P01-002 | MetadataManager | Mapped |
| SRS-501 | Quality Validation | SDS-P01-003 | QualityValidator | Mapped |
| SRS-601 | Schedule Execution | SDS-A01-001 | LaunchdManager | Mapped |
| SRS-701 | CLI Structure | SDS-I01-001 | CLI | Mapped |

### 10.2 SDS → Code Tracing

| SDS ID | File | Class/Function |
|--------|------|----------------|
| SDS-C01-001 | orchestrator.py | Orchestrator |
| SDS-C01-002 | config.py | Config |
| SDS-E01-002 | photos_extractor.py | PhotosExtractor |
| SDS-V01-002 | hardware_converter.py | HardwareConverter |
| SDS-V01-003 | software_converter.py | SoftwareConverter |
| SDS-P01-001 | codec_detector.py | CodecDetector |
| SDS-P01-002 | metadata_manager.py | MetadataManager |
| SDS-P01-003 | quality_validator.py | QualityValidator |
| SDS-A01-001 | launchd_manager.py | LaunchdManager |

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
| Observer | Progress monitoring | core/progress.py |

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
