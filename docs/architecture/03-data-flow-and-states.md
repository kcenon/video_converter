# Data Flow and State Diagrams

## 1. Data Flow Diagrams (DFD)

### 1.1 Context Diagram (Level 0)

```mermaid
graph LR
    USER((User))
    SYSTEM[Video Converter<br/>System]
    PHOTOS[(macOS Photos)]
    STORAGE[(File Storage)]
    ICLOUD[(iCloud)]

    USER -->|Settings, Commands| SYSTEM
    SYSTEM -->|Status, Notifications| USER

    PHOTOS -->|Original Videos| SYSTEM
    SYSTEM -->|Converted Videos| STORAGE

    ICLOUD -->|Cloud Videos| PHOTOS
```

### 1.2 Level 1 DFD

```mermaid
graph TB
    subgraph ExternalEntities["External Entities"]
        USER((User))
        PHOTOS[(Photos Library)]
        FS[(File System)]
    end

    subgraph Processes["Processes"]
        P1["1.0<br/>Video Extraction"]
        P2["2.0<br/>Codec Analysis"]
        P3["3.0<br/>Video Conversion"]
        P4["4.0<br/>Metadata Processing"]
        P5["5.0<br/>Quality Validation"]
        P6["6.0<br/>Result Reporting"]
    end

    subgraph DataStores["Data Stores"]
        D1[(Config File)]
        D2[(Conversion Log)]
        D3[(Processing Queue)]
        D4[(Statistics DB)]
    end

    USER -->|Settings| D1
    D1 -->|Config Values| P1
    D1 -->|Encoding Options| P3

    PHOTOS -->|Video List| P1
    P1 -->|Extracted Videos| D3
    D3 -->|Pending Videos| P2

    P2 -->|H.264 Videos| P3
    P2 -->|Already HEVC| P6

    P3 -->|Converted Videos| P4
    P3 -->|Progress| P6

    P4 -->|Metadata Restored| P5

    P5 -->|Validation Complete| FS
    P5 -->|Validation Failed| P3

    P6 -->|Notifications| USER
    P6 -->|Logs| D2
    P6 -->|Statistics| D4
```

### 1.3 Level 2 DFD - Video Conversion Process Details

```mermaid
graph TB
    subgraph VideoConversion["3.0 Video Conversion"]
        P3_1["3.1<br/>Input Validation"]
        P3_2["3.2<br/>FFmpeg Command Build"]
        P3_3["3.3<br/>Encoding Execution"]
        P3_4["3.4<br/>Progress Monitoring"]
        P3_5["3.5<br/>Error Handling"]
    end

    INPUT[Input Video] --> P3_1
    CONFIG[Encoding Config] --> P3_2

    P3_1 -->|Valid Input| P3_2
    P3_1 -->|Invalid Input| ERROR[Error Queue]

    P3_2 -->|FFmpeg Command| P3_3
    P3_3 -->|Progress Data| P3_4
    P3_3 -->|Error| P3_5

    P3_4 -->|Progress| PROGRESS[Progress Display]
    P3_5 -->|Retry| P3_3
    P3_5 -->|Failure| ERROR

    P3_3 -->|Success| OUTPUT[Output Video]
```

## 2. Data Transformation Flow

### 2.1 Video File Conversion Path

```mermaid
flowchart LR
    subgraph PhotosLibrary["Photos Library"]
        ORIG["Original H.264<br/>video.mov<br/>1.5GB"]
    end

    subgraph TempDirectory["Temp Directory"]
        EXPORT["Exported Copy<br/>video_export.mov<br/>1.5GB"]
    end

    subgraph Processing["Processing"]
        DECODE["H.264 Decode<br/>Raw Frames"]
        ENCODE["H.265 Encode<br/>VideoToolbox"]
    end

    subgraph OutputDirectory["Output Directory"]
        HEVC["Converted H.265<br/>video_hevc.mp4<br/>~750MB"]
    end

    subgraph ProcessedDirectory["Processed Directory"]
        BACKUP["Original Backup<br/>video.mov"]
    end

    ORIG -->|osxphotos export| EXPORT
    EXPORT -->|FFmpeg input| DECODE
    DECODE -->|Frame data| ENCODE
    ENCODE -->|FFmpeg output| HEVC
    EXPORT -->|After successful conversion| BACKUP
```

### 2.2 Metadata Flow

```mermaid
flowchart TB
    subgraph SourceMetadata["Source Metadata"]
        M1["QuickTime Metadata"]
        M2["EXIF/XMP Tags"]
        M3["GPS Coordinates"]
        M4["Creation Date"]
        M5["Camera Info"]
    end

    subgraph Extraction["Extraction"]
        FFPROBE["FFprobe<br/>Basic Metadata"]
        EXIFTOOL_R["ExifTool<br/>Detailed Metadata"]
    end

    subgraph TransferMethods["Transfer Methods"]
        MAP_META["FFmpeg<br/>-map_metadata 0"]
        TAG_COPY["ExifTool<br/>-tagsFromFile"]
        TOUCH["touch -r<br/>Timestamps"]
    end

    subgraph TargetMetadata["Target Metadata"]
        T1["QuickTime Metadata"]
        T2["EXIF/XMP Tags"]
        T3["GPS Coordinates"]
        T4["File Timestamps"]
    end

    M1 --> FFPROBE
    M2 --> EXIFTOOL_R
    M3 --> EXIFTOOL_R
    M4 --> EXIFTOOL_R
    M5 --> EXIFTOOL_R

    FFPROBE --> MAP_META
    EXIFTOOL_R --> TAG_COPY
    M4 --> TOUCH

    MAP_META --> T1
    TAG_COPY --> T2
    TAG_COPY --> T3
    TOUCH --> T4
```

## 3. State Diagrams

### 3.1 Video Processing States

```mermaid
stateDiagram-v2
    [*] --> Discovered: Video discovered

    Discovered --> Queued: Conversion target confirmed
    Discovered --> Skipped: Already HEVC

    Queued --> Exporting: Export started
    Exporting --> Exported: Export complete
    Exporting --> ExportFailed: Export failed

    ExportFailed --> Queued: Retry
    ExportFailed --> Failed: Max retries exceeded

    Exported --> Converting: Conversion started
    Converting --> Converted: Conversion successful
    Converting --> ConvertFailed: Conversion failed

    ConvertFailed --> Converting: Retry
    ConvertFailed --> Failed: Max retries exceeded

    Converted --> Validating: Quality validation
    Validating --> Validated: Validation passed
    Validating --> ConvertFailed: Validation failed

    Validated --> Finalizing: Metadata restoration
    Finalizing --> Completed: Complete

    Completed --> [*]
    Skipped --> [*]
    Failed --> [*]

    note right of Converting
        Progress updates
        0% → 100%
    end note

    note right of Failed
        Move to failed folder
        Log error
    end note
```

### 3.2 System Operation States

```mermaid
stateDiagram-v2
    [*] --> Idle: System started

    Idle --> Triggered: Trigger occurred
    note right of Triggered
        - Schedule time reached
        - Folder change detected
        - Manual execution
    end note

    Triggered --> Initializing: Initialization started
    Initializing --> Scanning: Scan started

    Scanning --> Processing: Targets found
    Scanning --> Idle: No targets

    Processing --> BatchRunning: Batch execution

    state BatchRunning {
        [*] --> ExtractingBatch
        ExtractingBatch --> ConvertingBatch
        ConvertingBatch --> FinalizingBatch
        FinalizingBatch --> [*]
    }

    BatchRunning --> Reporting: Batch complete

    Reporting --> Notifying: Report generated
    Notifying --> Cleaning: Notification sent

    Cleaning --> Idle: Cleanup complete

    Idle --> Shutdown: Shutdown requested
    Processing --> Shutdown: Force shutdown
    Shutdown --> [*]

    note right of Idle
        ThrottleInterval wait
        (default 30 seconds)
    end note
```

### 3.3 FFmpeg Process States

```mermaid
stateDiagram-v2
    [*] --> Ready: Command prepared

    Ready --> Spawning: Process creation
    Spawning --> Running: Process started

    Running --> Running: Processing frames
    note right of Running
        - Progress updates
        - CPU/Memory monitoring
    end note

    Running --> Succeeded: exit code 0
    Running --> Failed: exit code != 0
    Running --> Timeout: Timeout exceeded
    Running --> Cancelled: User cancelled

    Failed --> Analyzing: Error analysis
    Analyzing --> Retryable: Retryable error
    Analyzing --> NonRetryable: Non-retryable error

    Retryable --> Ready: After retry wait

    Succeeded --> [*]
    NonRetryable --> [*]
    Timeout --> [*]
    Cancelled --> [*]
```

## 4. Processing Queue Management

### 4.1 Queue State Transitions

```mermaid
stateDiagram-v2
    direction LR

    state PendingQueue {
        [*] --> Waiting
        Waiting --> Ready: Resources available
    }

    state ProcessingQueue {
        Ready --> InProgress: Worker assigned
        InProgress --> Completing: Processing complete
    }

    state CompletedQueue {
        Completing --> Success
        Completing --> Failure
    }

    PendingQueue --> ProcessingQueue: dequeue
    ProcessingQueue --> CompletedQueue: finish
    CompletedQueue --> PendingQueue: retry (on failure)
```

### 4.2 Concurrent Processing Management

```mermaid
graph TB
    subgraph QueueManager["Queue Manager"]
        PENDING[("Pending Queue<br/>Max 1000")]
        ACTIVE[("Active Queue<br/>Max 2")]
        DONE[("Completed Queue")]
        FAILED[("Failed Queue")]
    end

    subgraph Workers["Workers"]
        W1["Worker 1<br/>Hardware"]
        W2["Worker 2<br/>Hardware"]
    end

    PENDING -->|dequeue| W1
    PENDING -->|dequeue| W2

    W1 -->|success| DONE
    W1 -->|failure| FAILED

    W2 -->|success| DONE
    W2 -->|failure| FAILED

    FAILED -->|retry < 3| PENDING
```

## 5. Error States and Recovery

### 5.1 Error Classification and Handling

```mermaid
stateDiagram-v2
    [*] --> Error: Error occurred

    Error --> Analyzing: Error analysis

    state Analyzing {
        [*] --> Classify
        Classify --> Transient: Transient error
        Classify --> Permanent: Permanent error
        Classify --> Unknown: Unknown error
    }

    Transient --> RetryWithBackoff: Retryable
    note right of Transient
        - Network timeout
        - Resource shortage
        - iCloud sync delay
    end note

    Permanent --> LogAndSkip: Skip
    note right of Permanent
        - Corrupted file
        - Unsupported format
        - Permission denied
    end note

    Unknown --> LogAndRetry: Log and retry
    LogAndRetry --> RetryWithBackoff

    RetryWithBackoff --> Wait: Wait
    Wait --> [*]: Reprocess

    LogAndSkip --> MoveToFailed
    MoveToFailed --> [*]

    note right of Wait
        Backoff strategy:
        attempt 1: 5 seconds
        attempt 2: 10 seconds
        attempt 3: 20 seconds
    end note
```

### 5.2 Recovery Workflow

```mermaid
flowchart TB
    START[Error Occurred] --> CHECK_TYPE{Error Type?}

    CHECK_TYPE -->|File not found| FILE_ERROR[FileNotFound]
    CHECK_TYPE -->|Permission denied| PERM_ERROR[PermissionDenied]
    CHECK_TYPE -->|Disk space| DISK_ERROR[DiskSpace]
    CHECK_TYPE -->|FFmpeg error| FFMPEG_ERROR[FFmpegError]
    CHECK_TYPE -->|iCloud| ICLOUD_ERROR[iCloudError]

    FILE_ERROR --> SKIP[Skip]
    PERM_ERROR --> REQUEST_PERM[Request Permission Guide]

    DISK_ERROR --> CLEANUP[Clean Temp Files]
    CLEANUP --> RETRY{Space Available?}
    RETRY -->|Yes| PROCESS[Reprocess]
    RETRY -->|No| NOTIFY_USER[Notify User]

    FFMPEG_ERROR --> ANALYZE_CODE{Exit Code}
    ANALYZE_CODE -->|1| RETRY_SIMPLE[Simple Retry]
    ANALYZE_CODE -->|137| KILLED[Out of Memory]
    ANALYZE_CODE -->|Other| LOG_ERROR[Log Error]

    KILLED --> REDUCE_QUALITY[Reduce Quality Setting]
    REDUCE_QUALITY --> PROCESS

    ICLOUD_ERROR --> WAIT_SYNC[Wait for Sync]
    WAIT_SYNC --> PROCESS

    RETRY_SIMPLE --> PROCESS
    LOG_ERROR --> SKIP

    SKIP --> MOVE_FAILED[Move to Failed Folder]
    NOTIFY_USER --> END[End]
    PROCESS --> END
    REQUEST_PERM --> END
    MOVE_FAILED --> END
```

## 6. Configuration Data Structure

### 6.1 Configuration Hierarchy

```mermaid
graph TB
    subgraph ConfigHierarchy["Configuration Hierarchy"]
        DEFAULT["defaults.json<br/>Default Settings"]
        USER["User Settings<br/>~/.config/video_converter/"]
        PROJECT["Project Settings<br/>./video_converter.json"]
        CLI["CLI Arguments<br/>Command Line Args"]
        ENV["Environment Variables"]
    end

    DEFAULT --> MERGED["Merged Settings"]
    USER --> MERGED
    PROJECT --> MERGED
    CLI --> MERGED
    ENV --> MERGED

    MERGED --> VALIDATED["Validated Settings"]
    VALIDATED --> APP["Application"]
```

**Priority**: CLI > ENV > PROJECT > USER > DEFAULT

### 6.2 Runtime State Storage

```mermaid
erDiagram
    CONVERSION_STATE {
        string session_id PK
        datetime started_at
        datetime updated_at
        string status
        int total_videos
        int completed
        int failed
        int skipped
    }

    VIDEO_STATE {
        string video_id PK
        string session_id FK
        string original_path
        string output_path
        string status
        int attempt_count
        string last_error
        float progress
    }

    CHECKPOINT {
        string checkpoint_id PK
        string session_id FK
        datetime created_at
        blob state_snapshot
    }

    CONVERSION_STATE ||--o{ VIDEO_STATE : contains
    CONVERSION_STATE ||--o{ CHECKPOINT : has
```

## 7. Logging Data Flow

### 7.1 Log Collection and Storage

```mermaid
flowchart LR
    subgraph LogSources["Log Sources"]
        APP_LOG["Application Logs"]
        FFMPEG_LOG["FFmpeg Output"]
        SYSTEM_LOG["System Events"]
    end

    subgraph LogProcessor["Log Processor"]
        FORMATTER["Log Formatter"]
        FILTER["Log Filter"]
        ROUTER["Log Router"]
    end

    subgraph Destinations["Destinations"]
        FILE[("Log Files<br/>~/Library/Logs/")]
        CONSOLE["Console Output"]
        NOTIF["Notification Center"]
    end

    APP_LOG --> FORMATTER
    FFMPEG_LOG --> FORMATTER
    SYSTEM_LOG --> FORMATTER

    FORMATTER --> FILTER
    FILTER --> ROUTER

    ROUTER -->|DEBUG+| FILE
    ROUTER -->|INFO+| CONSOLE
    ROUTER -->|ERROR+| NOTIF
```
