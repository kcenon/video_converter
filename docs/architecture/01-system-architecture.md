# System Architecture

## 1. Overall System Structure

### 1.1 Layered Architecture

```mermaid
graph TB
    subgraph PresentationLayer["Presentation Layer"]
        CLI["CLI Interface"]
        NOTIF["macOS Notifications"]
        LOG_VIEW["Log Viewer"]
    end

    subgraph ApplicationLayer["Application Layer"]
        ORCH["Orchestrator"]
        SCHED["Scheduler"]
        CONFIG["Configuration Manager"]
    end

    subgraph DomainLayer["Domain Layer"]
        EXTRACTOR["Video Extractor"]
        DETECTOR["Codec Detector"]
        CONVERTER["Video Converter"]
        META["Metadata Manager"]
        VALIDATOR["Quality Validator"]
    end

    subgraph InfrastructureLayer["Infrastructure Layer"]
        PHOTOS_API["Photos API Adapter"]
        FFMPEG_API["FFmpeg Adapter"]
        EXIF_API["ExifTool Adapter"]
        FS["File System Manager"]
        LOGGER["Logger"]
    end

    subgraph ExternalSystems["External Systems"]
        PHOTOS[("macOS Photos Library")]
        FFMPEG_BIN["FFmpeg Binary"]
        EXIFTOOL_BIN["ExifTool Binary"]
        DISK[("File System")]
    end

    CLI --> ORCH
    NOTIF --> ORCH

    ORCH --> SCHED
    ORCH --> CONFIG
    ORCH --> EXTRACTOR
    ORCH --> CONVERTER

    EXTRACTOR --> DETECTOR
    CONVERTER --> META
    CONVERTER --> VALIDATOR

    EXTRACTOR --> PHOTOS_API
    DETECTOR --> FFMPEG_API
    CONVERTER --> FFMPEG_API
    META --> EXIF_API
    VALIDATOR --> FFMPEG_API

    PHOTOS_API --> PHOTOS
    FFMPEG_API --> FFMPEG_BIN
    EXIF_API --> EXIFTOOL_BIN
    FS --> DISK

    ORCH --> LOGGER
    LOGGER --> LOG_VIEW
```

### 1.2 Component Details

```mermaid
graph TB
    subgraph AppBoundary["Video Converter Application"]
        subgraph CoreComponents["Core Components"]
            scheduler["Scheduler<br/><i>launchd/Python</i>"]
            orchestrator["Orchestrator<br/><i>Python</i>"]
            config["Config Manager<br/><i>Python/JSON</i>"]
        end

        subgraph ProcessingComponents["Processing Components"]
            extractor["Video Extractor<br/><i>osxphotos</i>"]
            detector["Codec Detector<br/><i>FFprobe</i>"]
            converter["Video Converter<br/><i>FFmpeg</i>"]
            metadata["Metadata Manager<br/><i>ExifTool</i>"]
            validator["Quality Validator<br/><i>FFmpeg/VMAF</i>"]
        end

        subgraph OutputComponents["Output Components"]
            reporter["Reporter<br/><i>Python</i>"]
            notifier["Notifier<br/><i>AppleScript</i>"]
        end
    end

    subgraph ExternalSystems["External Systems"]
        photos[("macOS Photos<br/>Library")]
        filesystem[("File System<br/>Storage")]
    end

    scheduler -->|triggers| orchestrator
    orchestrator -->|extract request| extractor
    orchestrator -->|convert request| converter
    extractor -->|codec check| detector
    converter -->|metadata| metadata
    converter -->|validate| validator
    orchestrator -->|report| reporter
    orchestrator -->|notify| notifier

    extractor -->|read| photos
    converter -->|write| filesystem
```

### 1.3 Component Responsibilities

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| Scheduler | launchd/Python | Schedule/event-based execution management |
| Orchestrator | Python | Coordinate entire conversion workflow |
| Config Manager | Python/JSON | Configuration file management |
| Video Extractor | osxphotos | Extract videos from Photos library |
| Codec Detector | FFprobe | Analyze video codecs |
| Video Converter | FFmpeg | H.264→H.265 conversion |
| Metadata Manager | ExifTool | Metadata preservation/restoration |
| Quality Validator | FFmpeg/VMAF | Conversion quality validation |
| Reporter | Python | Statistics and report generation |
| Notifier | AppleScript | macOS notification delivery |

## 2. Module Structure

### 2.1 Package Diagram

```mermaid
graph TB
    subgraph video_converter["video_converter"]
        subgraph core["core"]
            ORCH_MOD["orchestrator.py"]
            CONFIG_MOD["config.py"]
            LOGGER_MOD["logger.py"]
        end

        subgraph extractors["extractors"]
            PHOTOS_EXT["photos_extractor.py"]
            FOLDER_EXT["folder_extractor.py"]
        end

        subgraph converters["converters"]
            HW_CONV["hardware_converter.py"]
            SW_CONV["software_converter.py"]
            CONV_BASE["base_converter.py"]
        end

        subgraph processors["processors"]
            CODEC_DET["codec_detector.py"]
            META_MGR["metadata_manager.py"]
            VALIDATOR["quality_validator.py"]
        end

        subgraph automation["automation"]
            LAUNCHD["launchd_manager.py"]
            FOLDER_WATCH["folder_watcher.py"]
        end

        subgraph reporters["reporters"]
            STATS["statistics.py"]
            NOTIF_MOD["notifier.py"]
        end
    end

    ORCH_MOD --> PHOTOS_EXT
    ORCH_MOD --> FOLDER_EXT
    ORCH_MOD --> HW_CONV
    ORCH_MOD --> SW_CONV
    PHOTOS_EXT --> CODEC_DET
    HW_CONV --> META_MGR
    SW_CONV --> META_MGR
    HW_CONV --> VALIDATOR
    ORCH_MOD --> STATS
    STATS --> NOTIF_MOD
```

### 2.2 Directory Structure

```
video_converter/
├── src/
│   └── video_converter/
│       ├── __init__.py
│       ├── main.py
│       ├── core/
│       │   ├── orchestrator.py
│       │   ├── config.py
│       │   └── logger.py
│       ├── extractors/
│       │   ├── base.py
│       │   ├── photos_extractor.py
│       │   └── folder_extractor.py
│       ├── converters/
│       │   ├── base.py
│       │   ├── hardware_converter.py
│       │   └── software_converter.py
│       ├── processors/
│       │   ├── codec_detector.py
│       │   ├── metadata_manager.py
│       │   └── quality_validator.py
│       ├── automation/
│       │   ├── launchd_manager.py
│       │   └── folder_watcher.py
│       ├── reporters/
│       │   ├── statistics.py
│       │   └── notifier.py
│       └── utils/
│           ├── file_utils.py
│           └── command_runner.py
├── config/
│   └── defaults.json
├── tests/
└── scripts/
    ├── install.sh
    └── uninstall.sh
```

## 3. Class Diagrams

### 3.1 Core Classes

```mermaid
classDiagram
    class Orchestrator {
        -config: Config
        -extractor: VideoExtractor
        -converter: VideoConverter
        -validator: QualityValidator
        -reporter: StatisticsReporter
        +run_batch(mode: str) BatchResult
        +convert_single(input: Path, output: Path) ConversionResult
        -_process_video(video: VideoInfo) ConversionResult
    }

    class Config {
        -data: dict
        -path: Path
        +load(path: Path) Config
        +save() void
        +get(key: str) Any
        +set(key: str, value: Any) void
    }

    class VideoExtractor {
        <<abstract>>
        +scan_videos() List~VideoInfo~
        +export_video(video: VideoInfo) Path
    }

    class VideoConverter {
        <<abstract>>
        +convert(request: ConversionRequest) ConversionResult
        #build_command(request: ConversionRequest) List~str~
    }

    Orchestrator --> Config
    Orchestrator --> VideoExtractor
    Orchestrator --> VideoConverter
```

### 3.2 Converter Hierarchy

```mermaid
classDiagram
    class VideoConverter {
        <<abstract>>
        +convert(request: ConversionRequest) ConversionResult
        #build_command(request: ConversionRequest) List~str~
        #execute_ffmpeg(command: List) void
    }

    class HardwareConverter {
        +convert(request: ConversionRequest) ConversionResult
        #build_command(request: ConversionRequest) List~str~
    }

    class SoftwareConverter {
        +convert(request: ConversionRequest) ConversionResult
        #build_command(request: ConversionRequest) List~str~
    }

    VideoConverter <|-- HardwareConverter
    VideoConverter <|-- SoftwareConverter
```

## 4. Data Flow

### 4.1 Conversion Pipeline

```mermaid
flowchart LR
    A[Photos Library] --> B[Video Extractor]
    B --> C{H.264?}
    C -->|Yes| D[Video Converter]
    C -->|No| E[Skip]
    D --> F[Metadata Manager]
    F --> G[Quality Validator]
    G --> H{Valid?}
    H -->|Yes| I[Output]
    H -->|No| J[Retry/Fail]
```

## 5. Deployment

### 5.1 Installation Structure

```
~/
├── Library/
│   ├── LaunchAgents/
│   │   └── com.user.videoconverter.plist
│   └── Logs/
│       └── video_converter/
├── .config/
│   └── video_converter/
│       ├── config.json
│       └── history.db
└── Videos/
    └── VideoConverter/
        ├── output/
        ├── processed/
        └── failed/
```

## 6. System Requirements

### 6.1 Hardware Requirements

| Item | Minimum | Recommended |
|------|---------|-------------|
| CPU | Apple M1 | Apple M2 Pro or better |
| RAM | 8GB | 16GB+ |
| Storage | 2x conversion target | 3x conversion target |

### 6.2 Software Requirements

| Software | Version | Installation |
|----------|---------|--------------|
| macOS | 12.0+ (Monterey) | - |
| Python | 3.10+ | `brew install python@3.12` |
| FFmpeg | 5.0+ | `brew install ffmpeg` |
| ExifTool | 12.0+ | `brew install exiftool` |
| osxphotos | 0.70+ | `pip install osxphotos` |

## 7. Auto-Generated Diagrams

The following diagrams are automatically generated from the codebase using pyreverse and pydeps.
These can be regenerated at any time by running:

```bash
python scripts/generate_diagrams.py
```

### 7.1 Package Structure

Full package dependency diagram showing all modules and their relationships:

![Package Structure](generated/packages_video_converter.svg)

### 7.2 Module Dependencies

Clustered dependency graph showing module relationships:

![Module Dependencies](generated/dependencies.svg)

### 7.3 Core Module Dependencies

Focused view of core module dependencies:

![Core Dependencies](generated/core_dependencies.svg)

### 7.4 Class Diagram

Complete UML class diagram (note: this is a large diagram):

![Class Diagram](generated/classes_video_converter.svg)
